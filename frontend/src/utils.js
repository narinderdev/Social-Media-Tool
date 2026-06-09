export const availablePlatformKeys = (platformItems, textOnly = false, hasMedia = false) =>
  platformItems
    .filter(
      (platform) =>
        platform.configured && !((textOnly || !hasMedia) && platform.key === "instagram")
    )
    .map((platform) => platform.key);

export const errorMessage = (error) => {
  if (typeof error === "string") {
    return error;
  }

  return error?.description || error?.detail || error?.message || "Could not create post.";
};

export const errorMessages = (data) => {
  const errors = data.errors || data.detail?.errors || data.detail || ["Could not create post."];
  return Array.isArray(errors) ? errors.map(errorMessage) : [errorMessage(errors)];
};

export const currentRoute = () => {
  if (window.location.pathname === "/posts") {
    return "posts";
  }
  if (window.location.pathname === "/scheduled") {
    return "scheduled";
  }
  return "dashboard";
};

export const mediaTypeForPost = (post) => {
  if (!post.media) {
    return "text";
  }
  return post.media.mimeType?.startsWith("video/") ? "video" : "photo";
};

export const publishTypeForPost = (post) => (post.scheduledAt ? "scheduled" : "instant");

export const isUpcomingScheduledPost = (post) =>
  ["scheduled", "publishing"].includes(post.status);
