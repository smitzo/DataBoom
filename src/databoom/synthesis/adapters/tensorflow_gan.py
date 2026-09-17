"""Owned optional TensorFlow GAN for bounded mixed-type tabular experiments."""

from __future__ import annotations

import importlib.util
import platform
import random
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from databoom.synthesis.adapters.base import SynthesizerUnavailableError
from databoom.synthesis.adapters.empirical import _require_output_path
from databoom.synthesis.adapters.tabular_encoding import decode_rows, encode_csv, write_rows
from databoom.synthesis.contracts import (
    AdapterAvailability,
    DatasetContract,
    DeterminismLevel,
    FitConfig,
    JsonScalar,
    ModelManifest,
    SampleArtifact,
    SynthesizerCapabilities,
)
from databoom.synthesis.io import (
    relative_to_root,
    resolve_within,
    sha256_file,
    stable_digest,
    stable_int_seed,
    write_model_json,
)

_DEPENDENCIES = ("numpy", "tensorflow")


class TensorflowGanAdapter:
    """Train a small owned GAN; promotion still depends on external quality gates."""

    @property
    def capabilities(self) -> SynthesizerCapabilities:
        missing = [name for name in _DEPENDENCIES if importlib.util.find_spec(name) is None]
        return SynthesizerCapabilities(
            name="tensorflow-gan",
            implementation_version="1",
            supports_missing_values=True,
            determinism=DeterminismLevel.BEST_EFFORT,
            complexity_tier=4,
            availability=(
                AdapterAvailability.AVAILABLE
                if not missing
                else AdapterAvailability.MISSING_DEPENDENCY
            ),
            dependency="tensorflow-cpu",
            dependency_version=_tensorflow_version() if not missing else None,
            dependency_license="Apache-2.0",
            unavailable_reason=(
                None
                if not missing
                else f"install the neural-tensorflow extra; missing: {', '.join(missing)}"
            ),
        )

    def fit(
        self,
        training_csv: Path,
        dataset: DatasetContract,
        experiment_root: Path,
        model_dir: Path,
        config: FitConfig,
    ) -> ModelManifest:
        dataset.require_training_eligible()
        self._require_available()
        import numpy as np
        import tensorflow as tf

        matrix, transform_metadata = encode_csv(training_csv, dataset, np)
        parameters = _validate_hyperparameters(config.hyperparameters)
        seed_value = stable_int_seed(config.seed, self.capabilities.name, "fit") % (2**31 - 1)
        _configure_determinism(seed_value, np, tf)
        generator = _build_generator(
            tf,
            latent_dim=parameters["latent_dim"],
            feature_count=matrix.shape[1],
            hidden_dim=parameters["hidden_dim"],
        )
        discriminator = _build_discriminator(
            tf,
            feature_count=matrix.shape[1],
            hidden_dim=parameters["hidden_dim"],
        )
        optimizer_options = {
            "learning_rate": parameters["learning_rate"],
            "beta_1": 0.5,
        }
        generator_optimizer = tf.keras.optimizers.Adam(**optimizer_options)
        discriminator_optimizer = tf.keras.optimizers.Adam(**optimizer_options)
        loss_function = tf.keras.losses.BinaryCrossentropy(from_logits=True)
        rng = np.random.default_rng(seed_value)
        real = np.asarray(matrix, dtype="float32")
        steps = max(1, (len(real) + parameters["batch_size"] - 1) // parameters["batch_size"])

        started = time.perf_counter()
        generator_loss = 0.0
        discriminator_loss = 0.0
        for _epoch in range(parameters["epochs"]):
            for _step in range(steps):
                batch_indexes = rng.integers(0, len(real), size=parameters["batch_size"])
                real_batch = tf.convert_to_tensor(real[batch_indexes], dtype=tf.float32)
                noise = tf.convert_to_tensor(
                    rng.normal(size=(parameters["batch_size"], parameters["latent_dim"])).astype(
                        "float32"
                    )
                )
                with tf.GradientTape() as discriminator_tape:
                    generated_batch = generator(noise, training=True)
                    real_logits = discriminator(real_batch, training=True)
                    fake_logits = discriminator(generated_batch, training=True)
                    discriminator_loss_tensor = loss_function(
                        tf.ones_like(real_logits), real_logits
                    ) + loss_function(tf.zeros_like(fake_logits), fake_logits)
                discriminator_gradients = discriminator_tape.gradient(
                    discriminator_loss_tensor, discriminator.trainable_variables
                )
                discriminator_optimizer.apply_gradients(
                    zip(discriminator_gradients, discriminator.trainable_variables, strict=True)
                )

                generator_noise = tf.convert_to_tensor(
                    rng.normal(size=(parameters["batch_size"], parameters["latent_dim"])).astype(
                        "float32"
                    )
                )
                with tf.GradientTape() as generator_tape:
                    generated_batch = generator(generator_noise, training=True)
                    fake_logits = discriminator(generated_batch, training=False)
                    generator_loss_tensor = loss_function(tf.ones_like(fake_logits), fake_logits)
                generator_gradients = generator_tape.gradient(
                    generator_loss_tensor, generator.trainable_variables
                )
                generator_optimizer.apply_gradients(
                    zip(generator_gradients, generator.trainable_variables, strict=True)
                )
                discriminator_loss = float(discriminator_loss_tensor.numpy())
                generator_loss = float(generator_loss_tensor.numpy())
        fit_seconds = time.perf_counter() - started

        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "tensorflow-generator.keras"
        generator.save(model_path, include_optimizer=False)
        artifact_sha256 = sha256_file(model_path)
        transform_metadata["__encoding__"] = {
            "feature_count": int(matrix.shape[1]),
            "latent_dim": parameters["latent_dim"],
            "final_generator_loss": generator_loss,
            "final_discriminator_loss": discriminator_loss,
        }
        manifest = ModelManifest(
            model_id="model_"
            + stable_digest(
                self.capabilities.name,
                sha256_file(training_csv),
                dataset.model_dump_json(),
                config.model_dump_json(),
                artifact_sha256,
            )[:24],
            adapter_name=self.capabilities.name,
            adapter_version=self.capabilities.implementation_version,
            dependency_versions={
                "python": platform.python_version(),
                "numpy": _package_version("numpy"),
                "tensorflow": _tensorflow_version(),
            },
            dependency_license="Apache-2.0",
            training_partition_sha256=sha256_file(training_csv),
            dataset_contract=dataset,
            hyperparameters=parameters,
            seed=config.seed,
            fit_seconds=fit_seconds,
            artifact_format="keras_v3",
            artifact_path=relative_to_root(experiment_root, model_path),
            artifact_sha256=artifact_sha256,
            transform_metadata=transform_metadata,
            warnings=(
                "This generic owned GAN is an experimental neural baseline; CTGAN or a "
                "classical model may perform better on mixed tabular data.",
                "TensorFlow determinism is best-effort across devices and package builds.",
                "A trained generator is not evidence of anonymity or production approval.",
            ),
        )
        write_model_json(model_dir / "model-manifest.json", manifest)
        return manifest

    def sample(
        self,
        manifest: ModelManifest,
        experiment_root: Path,
        output_path: Path,
        *,
        row_count: int,
        seed: str,
    ) -> SampleArtifact:
        if row_count <= 0:
            raise ValueError("sample row count must be positive")
        if manifest.adapter_name != self.capabilities.name:
            raise ValueError("model manifest belongs to a different adapter")
        self._require_available()
        import numpy as np
        import tensorflow as tf

        model_path = resolve_within(experiment_root, manifest.artifact_path)
        if sha256_file(model_path) != manifest.artifact_sha256:
            raise ValueError("model artifact checksum mismatch")
        seed_value = stable_int_seed(seed, self.capabilities.name, "sample") % (2**31 - 1)
        _configure_determinism(seed_value, np, tf)
        generator = tf.keras.models.load_model(
            model_path,
            compile=False,
            safe_mode=True,
        )
        latent_dim = int(manifest.transform_metadata["__encoding__"]["latent_dim"])
        rng = np.random.default_rng(seed_value)
        noise = rng.normal(size=(row_count, latent_dim)).astype("float32")
        started = time.perf_counter()
        encoded = generator.predict(noise, batch_size=min(row_count, 1024), verbose=0)
        transform_metadata = {
            name: settings
            for name, settings in manifest.transform_metadata.items()
            if name != "__encoding__"
        }
        rows = decode_rows(encoded, manifest.dataset_contract, transform_metadata, np)
        output_path = _require_output_path(experiment_root, output_path)
        write_rows(output_path, manifest.dataset_contract, rows)
        return SampleArtifact(
            path=relative_to_root(experiment_root, output_path),
            row_count=row_count,
            seed=seed,
            sample_seconds=time.perf_counter() - started,
            sha256=sha256_file(output_path),
        )

    def _require_available(self) -> None:
        capabilities = self.capabilities
        if capabilities.availability != AdapterAvailability.AVAILABLE:
            raise SynthesizerUnavailableError(
                capabilities.unavailable_reason or "TensorFlow provider unavailable"
            )


def _build_generator(tf: Any, *, latent_dim: int, feature_count: int, hidden_dim: int) -> Any:
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(latent_dim,)),
            tf.keras.layers.Dense(hidden_dim),
            tf.keras.layers.LeakyReLU(negative_slope=0.2),
            tf.keras.layers.Dense(hidden_dim),
            tf.keras.layers.LeakyReLU(negative_slope=0.2),
            tf.keras.layers.Dense(feature_count, activation="sigmoid"),
        ],
        name="databoom_tabular_generator",
    )


def _build_discriminator(tf: Any, *, feature_count: int, hidden_dim: int) -> Any:
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(feature_count,)),
            tf.keras.layers.Dense(hidden_dim),
            tf.keras.layers.LeakyReLU(negative_slope=0.2),
            tf.keras.layers.Dense(max(16, hidden_dim // 2)),
            tf.keras.layers.LeakyReLU(negative_slope=0.2),
            tf.keras.layers.Dense(1),
        ],
        name="databoom_tabular_discriminator",
    )


def _validate_hyperparameters(values: dict[str, JsonScalar]) -> dict[str, Any]:
    defaults: dict[str, int | float] = {
        "epochs": 100,
        "batch_size": 256,
        "latent_dim": 64,
        "hidden_dim": 128,
        "learning_rate": 0.0002,
    }
    unknown = set(values) - set(defaults)
    if unknown:
        raise ValueError(
            f"unsupported TensorFlow GAN hyperparameters: {', '.join(sorted(unknown))}"
        )
    result = {**defaults, **values}
    for name, maximum in (
        ("epochs", 100_000),
        ("batch_size", 16_384),
        ("latent_dim", 2_048),
        ("hidden_dim", 4_096),
    ):
        value = result[name]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    learning_rate = result["learning_rate"]
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be numeric")
    if not 0 < float(learning_rate) <= 1:
        raise ValueError("learning_rate must be greater than 0 and at most 1")
    return result


def _configure_determinism(seed: int, numpy: Any, tf: Any) -> None:
    random.seed(seed)
    numpy.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        pass


def _tensorflow_version() -> str:
    value = _package_version("tensorflow-cpu")
    if value == "unknown":
        value = _package_version("tensorflow")
    return value


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"
