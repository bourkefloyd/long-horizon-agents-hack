export type AdManifestItem = {
  id: string;
  campaign_id: string;
  variant_id: string;
  hook: string;
  cta: string;
  media_type: "video" | "image" | "playable" | "script";
  media_url: string;
  poster_url?: string;
  duration_s?: number;
  aspect: "9:16";
  script?: string;
  targeting: {
    audience?: string;
    geo?: string;
    weight: number;
    active: boolean;
  };
  source: {
    agent: string;
    generated_at: string;
  };
};

// These five script-backed previews come from content/ads/scripts.json. The
// source branch describes generated video files, but does not include the
// media or stable hosted URLs, so media_url is empty and the feed renders the
// script. This matches the CDN manifest schema so fetchAdManifest() can replace
// it while retaining this array as the local fallback.
export const localAdManifest: AdManifestItem[] = [
  {
    id: "ad-sightglass-founder",
    campaign_id: "demo",
    variant_id: "sightglass__soma_founder",
    hook: "Demo day. Four minutes to make it count.",
    cta: "Watch the pitch",
    media_type: "script",
    media_url: "",
    duration_s: 10,
    aspect: "9:16",
    script:
      "Eight missed messages. One last sidewalk rehearsal before the room opens. She steps into the bright SoMa roastery and waits at the bar. Coffee in hand, she walks toward demo day with her shoulders back. VO: “Demo day. Four minutes to make it count. Sightglass. Roasted right here on 7th Street.”",
    targeting: {
      audience: "SoMa startup founders",
      geo: "San Francisco, CA",
      weight: 1,
      active: true,
    },
    source: {
      agent: "complide/wonderful-faraday-eoinzh",
      generated_at: "2026-09-25T00:00:00Z",
    },
  },
  {
    id: "ad-tartine-surfer",
    campaign_id: "demo",
    variant_id: "tartine__ocean_beach_surfer",
    hook: "Fifty-five degree water. Worth it.",
    cta: "Find your morning bun",
    media_type: "script",
    media_url: "",
    duration_s: 10,
    aspect: "9:16",
    script:
      "She jogs out of the gray Ocean Beach surf, shivering in her wetsuit. Wrapped in a towel, she opens a warm paper bag at the van. Sugar on her lips, she closes her eyes while the waves roll behind her. VO: “Fifty-five degree water. Worth it. Tartine morning bun. The real reward.”",
    targeting: {
      audience: "Ocean Beach surfers",
      geo: "San Francisco, CA",
      weight: 1,
      active: true,
    },
    source: {
      agent: "complide/wonderful-faraday-eoinzh",
      generated_at: "2026-09-25T00:00:00Z",
    },
  },
  {
    id: "ad-birite-park",
    campaign_id: "demo",
    variant_id: "bi_rite__dolores_park_crew",
    hook: "Hottest Sunday of the year.",
    cta: "Meet us on 18th",
    media_type: "script",
    media_url: "",
    duration_s: 10,
    aspect: "9:16",
    script:
      "The sun beats down on the park while four friends fan themselves. One points toward the cheerful line forming on 18th Street. Four salted-caramel cones clink together above the skyline. VO: “Hottest Sunday of the year. You know where the line is. Bi-Rite Creamery. Twenty years on 18th Street.”",
    targeting: {
      audience: "Dolores Park groups",
      geo: "San Francisco, CA",
      weight: 1,
      active: true,
    },
    source: {
      agent: "complide/wonderful-faraday-eoinzh",
      generated_at: "2026-09-25T00:00:00Z",
    },
  },
  {
    id: "ad-dandelion-founder",
    campaign_id: "demo",
    variant_id: "dandelion__soma_founder",
    hook: "They said yes.",
    cta: "Make the win sweeter",
    media_type: "script",
    media_url: "",
    duration_s: 10,
    aspect: "9:16",
    script:
      "Her phone buzzes outside a glass office. She reads the message twice. Laughing in disbelief, she steps into a warm Valencia Street cafe. She raises a cup of hot chocolate in a quiet solo toast. VO: “They said yes. Dandelion Chocolate. Bean to bar, on Valencia since 2012.”",
    targeting: {
      audience: "SoMa startup founders",
      geo: "San Francisco, CA",
      weight: 1,
      active: true,
    },
    source: {
      agent: "complide/wonderful-faraday-eoinzh",
      generated_at: "2026-09-25T00:00:00Z",
    },
  },
  {
    id: "ad-boudin-transplant",
    campaign_id: "demo",
    variant_id: "boudin__new_transplant",
    hook: "Nobody told me July would be this cold.",
    cta: "Warm up with sourdough",
    media_type: "script",
    media_url: "",
    duration_s: 10,
    aspect: "9:16",
    script:
      "She stares at 58° on her phone while fog swallows the waterfront. The smell of fresh bread pulls her through a bakery doorway. Steam rises from a torn loaf as she finally grins at the fog. VO: “Nobody told me July would be this cold. Boudin. San Francisco sourdough since 1849.”",
    targeting: {
      audience: "New San Francisco residents",
      geo: "San Francisco, CA",
      weight: 1,
      active: true,
    },
    source: {
      agent: "complide/wonderful-faraday-eoinzh",
      generated_at: "2026-09-25T00:00:00Z",
    },
  },
];
