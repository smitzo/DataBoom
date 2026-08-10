import { Section } from "@/components/layout";
import { Timeline } from "@/components/timeline";
import { roadmap } from "@/data/workbench";

export function Roadmap() {
  return (
    <Section
      id="roadmap"
      eyebrow="Roadmap"
      title="A staged platform roadmap, not a pile of disconnected features."
      subtitle="Each phase is represented as structured timeline data. Add a new phase by adding text, status, and sections to the roadmap data source."
    >
      <Timeline
        items={roadmap.map((item) => ({
          id: item.id,
          eyebrow: item.phase,
          status: item.status,
          title: item.title,
          description: item.description,
          sections: item.sections,
        }))}
      />
    </Section>
  );
}
