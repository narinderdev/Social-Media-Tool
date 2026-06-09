export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:4000";

export const APP_NAME = "Social Media Tool";

export const platformStyles = {
  instagram: { name: "Instagram", tone: "rose" },
  facebook: { name: "Facebook", tone: "blue" },
  linkedin: { name: "LinkedIn", tone: "indigo" },
  twitter: { name: "X / Twitter", tone: "stone" }
};

export const fallbackPlatforms = Object.entries(platformStyles).map(([key, platform]) => ({
  key,
  label: platform.name,
  configured: false,
  offline: true
}));

export const initialForm = {
  caption: "",
  textOnly: false,
  platforms: [],
  media: null
};
