export type AdManifestItem = {
  id: string;
  campaignId: string;
  variant: string;
  brand: string;
  hook: string;
  cta: string;
  mediaType: "script";
  mediaPath?: string;
  script: {
    tension: string;
    turn: string;
    payoff: string;
    voiceover: string[];
  };
  accent: {
    from: string;
    via: string;
    to: string;
  };
};

// These five script-backed previews come from content/ads/scripts.json. The
// source branch describes generated video files, but does not include the
// media or stable hosted URLs, so the feed renders the scripts directly.
export const adManifest: AdManifestItem[] = [
  {
    id: "ad-sightglass-founder",
    campaignId: "demo",
    variant: "sightglass__soma_founder",
    brand: "Sightglass Coffee",
    hook: "Demo day. Four minutes to make it count.",
    cta: "Watch the pitch",
    mediaType: "script",
    script: {
      tension:
        "Eight missed messages. One last sidewalk rehearsal before the room opens.",
      turn: "She steps into the bright SoMa roastery and waits at the bar.",
      payoff:
        "Coffee in hand, she walks toward demo day with her shoulders back.",
      voiceover: [
        "Demo day. Four minutes to make it count.",
        "Sightglass. Roasted right here on 7th Street.",
      ],
    },
    accent: { from: "#071b2b", via: "#31515a", to: "#d5b887" },
  },
  {
    id: "ad-tartine-surfer",
    campaignId: "demo",
    variant: "tartine__ocean_beach_surfer",
    brand: "Tartine Bakery",
    hook: "Fifty-five degree water. Worth it.",
    cta: "Find your morning bun",
    mediaType: "script",
    script: {
      tension:
        "She jogs out of the gray Ocean Beach surf, shivering in her wetsuit.",
      turn: "Wrapped in a towel, she opens a warm paper bag at the van.",
      payoff:
        "Sugar on her lips, she closes her eyes while the waves roll behind her.",
      voiceover: [
        "Fifty-five degree water. Worth it.",
        "Tartine morning bun. The real reward.",
      ],
    },
    accent: { from: "#15354a", via: "#df8d55", to: "#f6d991" },
  },
  {
    id: "ad-birite-park",
    campaignId: "demo",
    variant: "bi_rite__dolores_park_crew",
    brand: "Bi-Rite Creamery",
    hook: "Hottest Sunday of the year.",
    cta: "Meet us on 18th",
    mediaType: "script",
    script: {
      tension:
        "The sun beats down on the park while four friends fan themselves.",
      turn: "One points toward the cheerful line forming on 18th Street.",
      payoff:
        "Four salted-caramel cones clink together above the skyline.",
      voiceover: [
        "Hottest Sunday of the year. You know where the line is.",
        "Bi-Rite Creamery. Twenty years on 18th Street.",
      ],
    },
    accent: { from: "#59284f", via: "#df5b78", to: "#ffcf8b" },
  },
  {
    id: "ad-dandelion-founder",
    campaignId: "demo",
    variant: "dandelion__soma_founder",
    brand: "Dandelion Chocolate",
    hook: "They said yes.",
    cta: "Make the win sweeter",
    mediaType: "script",
    script: {
      tension:
        "Her phone buzzes outside a glass office. She reads the message twice.",
      turn: "Laughing in disbelief, she steps into a warm Valencia Street cafe.",
      payoff:
        "She raises a cup of hot chocolate in a quiet solo toast.",
      voiceover: [
        "They said yes.",
        "Dandelion Chocolate. Bean to bar, on Valencia since 2012.",
      ],
    },
    accent: { from: "#21120d", via: "#75452d", to: "#d9ad74" },
  },
  {
    id: "ad-boudin-transplant",
    campaignId: "demo",
    variant: "boudin__new_transplant",
    brand: "Boudin Bakery",
    hook: "Nobody told me July would be this cold.",
    cta: "Warm up with sourdough",
    mediaType: "script",
    script: {
      tension:
        "She stares at 58° on her phone while fog swallows the waterfront.",
      turn: "The smell of fresh bread pulls her through a bakery doorway.",
      payoff:
        "Steam rises from a torn loaf as she finally grins at the fog.",
      voiceover: [
        "Nobody told me July would be this cold.",
        "Boudin. San Francisco sourdough since 1849.",
      ],
    },
    accent: { from: "#26343f", via: "#6e8791", to: "#e6b968" },
  },
];
