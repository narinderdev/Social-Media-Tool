import { FileText, ImagePlus, Loader2, Send, UploadCloud, X } from "lucide-react";

import { fallbackPlatforms, platformStyles } from "../constants";

function DashboardView({
  form,
  accounts,
  activePlatforms,
  selectedPublishAccounts,
  previewUrl,
  selectedPlatformLabels,
  canSubmit,
  submitting,
  setForm,
  updateTextOnly,
  updatePlatform,
  submitPost
}) {
  const visiblePlatforms = activePlatforms.length > 0 ? activePlatforms : fallbackPlatforms;
  const accountReady = (account) => account.platforms.every((platform) => platform.configured);
  const accountMissingText = (account) =>
    account.platforms
      .filter((platform) => !platform.configured)
      .map((platform) => `${platform.label}: ${platform.missingEnv.join(", ")}`)
      .join(" | ");

  const updatePublishAccount = (accountKey, checked) => {
    setForm((current) => {
      const nextAccounts = checked
        ? [...current.selectedAccounts, accountKey]
        : current.selectedAccounts.filter((item) => item !== accountKey);

      return {
        ...current,
        selectedAccounts: [...new Set(nextAccounts)]
      };
    });
  };

  const removeMedia = () => {
    setForm((current) => ({
      ...current,
      media: null,
      platforms: current.platforms.filter((platform) => platform !== "instagram")
    }));
  };

  return (
    <section className="workspace">
      <form className="composer-panel" onSubmit={submitPost}>
        <div className="panel-heading">
          <h2>New post</h2>
          <span>{selectedPlatformLabels || "No platform selected"}</span>
        </div>

        <label className="field-label" htmlFor="caption">
          Caption
        </label>
        <textarea
          id="caption"
          value={form.caption}
          onChange={(event) => setForm((current) => ({ ...current, caption: event.target.value }))}
          placeholder="Write text for the post"
          rows={7}
        />

        <div className="mode-row">
          <button
            className={!form.textOnly ? "mode-button active" : "mode-button"}
            type="button"
            onClick={() => updateTextOnly(false)}
          >
            <ImagePlus size={17} />
            Media
          </button>
          <button
            className={form.textOnly ? "mode-button active" : "mode-button"}
            type="button"
            onClick={() => updateTextOnly(true)}
          >
            <FileText size={17} />
            Text only
          </button>
        </div>

        {!form.textOnly && (
          <label className="upload-zone">
            <UploadCloud size={28} />
            <span>{form.media ? form.media.name : "Choose image or video"}</span>
            <input
              key={form.media ? form.media.name : "empty-media"}
              type="file"
              accept="image/*,video/*"
              onChange={(event) =>
                setForm((current) => {
                  const media = event.target.files?.[0] || null;
                  const instagramReady = activePlatforms.some(
                    (platform) => platform.key === "instagram" && platform.configured
                  );
                  return {
                    ...current,
                    media,
                    platforms: media
                      ? [...new Set([...current.platforms, ...(instagramReady ? ["instagram"] : [])])]
                      : current.platforms.filter((platform) => platform !== "instagram")
                  };
                })
              }
            />
          </label>
        )}

        <fieldset>
          <legend>Platforms</legend>
          <div className="platform-grid">
            {visiblePlatforms.map((platform) => {
              const disabled =
                !platform.configured ||
                ((form.textOnly || !form.media) && platform.key === "instagram");
              const selected = form.platforms.includes(platform.key);
              const style = platformStyles[platform.key] || { name: platform.label, tone: "stone" };

              return (
                <label className={`platform-option ${style.tone}`} key={platform.key}>
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={disabled}
                    onChange={(event) => updatePlatform(platform.key, event.target.checked)}
                  />
                  <span>
                    <strong>{platform.label}</strong>
                    <small>
                      {platform.offline ? "API offline" : platform.configured ? "Ready" : "Needs keys"}
                    </small>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="schedule-panel">
          <legend>Publish time</legend>
          <div className="schedule-options">
            <label className="schedule-option">
              <input
                type="radio"
                name="publishMode"
                value="instant"
                checked={form.publishMode === "instant"}
                onChange={() =>
                  setForm((current) => ({
                    ...current,
                    publishMode: "instant",
                    scheduledDate: "",
                    scheduledTime: ""
                  }))
                }
              />
              <span>
                <strong>Post instant</strong>
                <small>Publish as soon as you submit.</small>
              </span>
            </label>

            <label className="schedule-option">
              <input
                type="radio"
                name="publishMode"
                value="scheduled"
                checked={form.publishMode === "scheduled"}
                onChange={() =>
                  setForm((current) => ({
                    ...current,
                    publishMode: "scheduled"
                  }))
                }
              />
              <span>
                <strong>Schedule</strong>
                <small>Pick a future date and time.</small>
              </span>
            </label>
          </div>

          {form.publishMode === "scheduled" && (
            <div className="schedule-fields">
              <input
                className="text-input schedule-input"
                type="date"
                value={form.scheduledDate}
                onChange={(event) =>
                  setForm((current) => ({ ...current, scheduledDate: event.target.value }))
                }
                required
              />
              <input
                className="text-input schedule-input"
                type="time"
                value={form.scheduledTime}
                onChange={(event) =>
                  setForm((current) => ({ ...current, scheduledTime: event.target.value }))
                }
                required
              />
            </div>
          )}
        </fieldset>

        <fieldset className="publish-account-panel">
          <legend>Post to account</legend>
          <div className="account-checkbox-list">
            {accounts.map((account) => {
              const ready = accountReady(account);
              return (
                <label className="account-checkbox-option" key={account.key}>
                  <input
                    type="checkbox"
                    checked={form.selectedAccounts.includes(account.key)}
                    disabled={!ready}
                    onChange={(event) => updatePublishAccount(account.key, event.target.checked)}
                  />
                  <span>
                    <strong>{account.label}</strong>
                    <small>{ready ? "Ready" : `Missing env: ${accountMissingText(account)}`}</small>
                  </span>
                </label>
              );
            })}
          </div>
          <p className="helper-text">
            Selected:{" "}
            {selectedPublishAccounts.length > 0
              ? selectedPublishAccounts.map((account) => account.label).join(", ")
              : "No account selected"}
          </p>
        </fieldset>

        <button className="submit-button" type="submit" disabled={!canSubmit || submitting}>
          {submitting ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          {form.publishMode === "scheduled" ? "Schedule post" : "Post everywhere"}
        </button>
      </form>

      <aside className="preview-panel">
        <div className="panel-heading">
          <h2>Preview</h2>
          {previewUrl ? (
            <button className="remove-media-button" type="button" onClick={removeMedia}>
              <X size={15} />
              Remove media
            </button>
          ) : (
            <span>{form.textOnly ? "Text" : "Media"}</span>
          )}
        </div>

        {previewUrl ? (
          form.media?.type.startsWith("video/") ? (
            <video className="media-preview" src={previewUrl} controls />
          ) : (
            <img className="media-preview" src={previewUrl} alt="" />
          )
        ) : (
          <div className="empty-preview">
            {form.textOnly ? <FileText size={42} /> : <ImagePlus size={42} />}
          </div>
        )}

        <p className="preview-caption">{form.caption || "Caption will appear here."}</p>
      </aside>
    </section>
  );
}

export default DashboardView;
