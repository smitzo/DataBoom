import { Hero } from "@/components/hero";
import { PublicShell } from "@/components/layout";
import { MarketingStory } from "@/components/marketing-sections";

export default function Home() {
  return (
    <PublicShell>
      <Hero />
      <MarketingStory />
    </PublicShell>
  );
}
