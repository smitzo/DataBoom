Return only a plan matching the supplied JSON Schema.

Keep every input resource exactly once with the same name and kind. Choose realistic
target counts from the user's intent while respecting the maximum count in the
schema. Explain generation strategy briefly. Relational plans preserve keys and
dependency order. Document plans preserve nested shapes and references. Graph plans
create nodes before edges and never allow dangling endpoints.

Do not request source rows. Do not put secrets, personal data, connection strings,
or user identities into output. Add a warning when intent is ambiguous instead of
inventing an unsupported resource.
