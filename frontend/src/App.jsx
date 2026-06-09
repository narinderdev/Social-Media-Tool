import { useEffect, useMemo, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { apiFetch, parseJsonResponse } from "./api";
import AccountSelector from "./components/AccountSelector";
import ConfirmModal from "./components/ConfirmModal";
import DashboardView from "./components/DashboardView";
import HistoryView from "./components/HistoryView";
import LoadingScreen from "./components/LoadingScreen";
import LoginPage from "./components/LoginPage";
import ScheduledView from "./components/ScheduledView";
import Sidebar from "./components/Sidebar";
import ToastStack from "./components/ToastStack";
import { APP_NAME, initialForm, platformStyles } from "./constants";
import {
  availablePlatformKeys,
  currentRoute,
  errorMessages,
  isUpcomingScheduledPost
} from "./utils";

function App() {
  const [form, setForm] = useState(initialForm);
  const [accounts, setAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [previewUrl, setPreviewUrl] = useState("");
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authStatus, setAuthStatus] = useState("checking");
  const [user, setUser] = useState(null);
  const [route, setRoute] = useState(currentRoute);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [toasts, setToasts] = useState([]);

  const selectedPlatformLabels = useMemo(
    () =>
      form.platforms
        .map((platform) => platformStyles[platform]?.name || platform)
        .join(", "),
    [form.platforms]
  );
  const selectedAccount = useMemo(
    () => accounts.find((account) => account.key === form.selectedAccount),
    [accounts, form.selectedAccount]
  );
  const activePlatforms = selectedAccount?.platforms || [];
  const accountMissingKeys = useMemo(
    () =>
      activePlatforms
        .filter((platform) => !platform.configured)
        .map((platform) => `${platform.label}: ${platform.missingEnv.join(", ")}`),
    [activePlatforms]
  );

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      if (authStatus !== "authenticated") {
        window.history.replaceState({}, "", "/login");
        return;
      }

      if (!["/dashboard", "/posts", "/scheduled"].includes(window.location.pathname)) {
        window.history.replaceState({}, "", "/dashboard");
      }
      setRoute(currentRoute());
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [authStatus]);

  useEffect(() => {
    if (!form.media) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreviewUrl = URL.createObjectURL(form.media);
    setPreviewUrl(nextPreviewUrl);
    return () => URL.revokeObjectURL(nextPreviewUrl);
  }, [form.media]);

  const handleUnauthorized = () => {
    setAuthStatus("anonymous");
    setUser(null);
    setPosts([]);
    setAccounts([]);
    setErrors([]);
    window.history.replaceState({}, "", "/login");
  };

  const checkSession = async () => {
    setAuthStatus("checking");
    setSessionError("");
    try {
      const response = await apiFetch("/api/auth/session");
      const data = await response.json();
      if (!response.ok || !data.user) {
        handleUnauthorized();
        return;
      }

      setUser(data.user);
      setAuthStatus("authenticated");
      if (!["/dashboard", "/posts", "/scheduled"].includes(window.location.pathname)) {
        window.history.replaceState({}, "", "/dashboard");
      }
      setRoute(currentRoute());
      await loadDashboard(true);
    } catch {
      setAuthStatus("unavailable");
      setSessionError("Backend is not reachable. Start the API server first, then retry.");
    }
  };

  const dismissToast = (id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  };

  const showToast = (message, type = "info") => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, type }]);
    window.setTimeout(() => dismissToast(id), 3500);
  };

  const loadDashboard = async (sessionConfirmed = false, options = {}) => {
    if (!sessionConfirmed && authStatus !== "authenticated") {
      return;
    }

    setLoading(true);
    setErrors([]);

    try {
      const [platformResponse, postsResponse] = await Promise.all([
        apiFetch("/api/accounts"),
        apiFetch("/api/posts")
      ]);

      if (platformResponse.status === 401 || postsResponse.status === 401) {
        handleUnauthorized();
        return;
      }

      const accountData = await platformResponse.json();
      const postsData = await postsResponse.json();
      const nextAccounts = accountData.accounts || [];

      setAccounts(nextAccounts);
      setPosts(postsData.posts || []);
      setForm((current) => ({
        ...current,
        ...(() => {
          const nextAccount =
            nextAccounts.find((account) => account.key === current.selectedAccount) ||
            nextAccounts.find((account) => account.key === accountData.defaultAccount) ||
            nextAccounts[0];
          const nextPlatforms = nextAccount?.platforms || [];
          const availablePlatforms = availablePlatformKeys(
            nextPlatforms,
            current.textOnly,
            Boolean(current.media)
          );
          return {
            selectedAccount: nextAccount?.key || "",
            platforms:
              current.platforms.length > 0
                ? current.platforms.filter((platform) => availablePlatforms.includes(platform))
                : availablePlatforms
          };
        })()
      }));
      if (options.toastMessage) {
        showToast(options.toastMessage, "success");
      }
    } catch {
      const message = "Backend is not reachable. Start the API server first.";
      setErrors([message]);
      showToast(message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus !== "authenticated" || route !== "scheduled") {
      return undefined;
    }

    const intervalId = window.setInterval(() => loadDashboard(false), 30000);
    return () => window.clearInterval(intervalId);
  }, [authStatus, route]);

  const navigate = (nextRoute) => {
    const path =
      nextRoute === "posts" ? "/posts" : nextRoute === "scheduled" ? "/scheduled" : "/dashboard";
    window.history.pushState({}, "", path);
    setRoute(nextRoute);
    if (nextRoute === "posts") {
      loadDashboard(false, { toastMessage: "History fetched." });
    }
    if (nextRoute === "scheduled") {
      loadDashboard(false, { toastMessage: "Scheduled posts fetched." });
    }
  };

  const changeAccount = (accountKey) => {
    const nextAccount = accounts.find((account) => account.key === accountKey);
    const nextPlatforms = nextAccount?.platforms || [];
    setForm((current) => ({
      ...current,
      selectedAccount: accountKey,
      platforms: availablePlatformKeys(nextPlatforms, current.textOnly, Boolean(current.media))
    }));
    setErrors([]);
  };

  const upsertPost = (post) => {
    setPosts((current) => [post, ...current.filter((item) => item.id !== post.id)]);
  };

  const updatePlatform = (platform, checked) => {
    setForm((current) => {
      const nextPlatforms = checked
        ? [...current.platforms, platform]
        : current.platforms.filter((item) => item !== platform);

      return { ...current, platforms: [...new Set(nextPlatforms)] };
    });
  };

  const updateTextOnly = (checked) => {
    setForm((current) => ({
      ...current,
      textOnly: checked,
      media: checked ? null : current.media,
      platforms: checked
        ? current.platforms.filter((platform) => platform !== "instagram")
        : current.platforms
    }));
  };

  const submitPost = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setErrors([]);

    const payload = new FormData();
    payload.append("caption", form.caption);
    payload.append("textOnly", String(form.textOnly));
    payload.append("platforms", JSON.stringify(form.platforms));
    payload.append("account", form.selectedAccount);
    payload.append("scheduleMode", form.publishMode);
    payload.append(
      "scheduledAt",
      form.publishMode === "scheduled" ? `${form.scheduledDate}T${form.scheduledTime}` : ""
    );

    if (form.media && !form.textOnly) {
      payload.append("media", form.media);
    }

    try {
      const response = await apiFetch("/api/posts", {
        method: "POST",
        body: payload
      });
      const data = await response.json();

      if (response.status === 401) {
        handleUnauthorized();
        return;
      }

      if (!response.ok) {
        const partialPost = data.post || data.detail?.post;
        if (partialPost) {
          upsertPost(partialPost);
          setForm({
            ...initialForm,
            selectedAccount: form.selectedAccount,
            platforms: availablePlatformKeys(activePlatforms)
          });
        }
        const nextErrors = errorMessages(data);
        setErrors(nextErrors);
        showToast(partialPost ? "Post partially completed. Check errors." : nextErrors[0], "error");
        return;
      }

      upsertPost(data.post);
      setForm({
        ...initialForm,
        selectedAccount: form.selectedAccount,
        platforms: availablePlatformKeys(activePlatforms)
      });
      showToast(
        form.publishMode === "scheduled" ? "Post scheduled successfully." : "Post published successfully.",
        "success"
      );
    } catch {
      const message = "Post request failed. Check that the backend is running.";
      setErrors([message]);
      showToast(message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const login = async (credentials) => {
    const data = await parseJsonResponse(
      await apiFetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials)
      })
    );

    setUser(data.user);
    setAuthStatus("authenticated");
    window.history.replaceState({}, "", "/dashboard");
    setRoute("dashboard");
    await loadDashboard(true);
    showToast("Login successful.", "success");
  };

  const logout = async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
      setShowLogoutModal(false);
      handleUnauthorized();
      showToast("Logged out successfully.", "success");
    } catch {
      showToast("Logout failed. Check the backend connection.", "error");
    }
  };

  const historyPosts = useMemo(
    () =>
      posts.filter(
        (post) =>
          !isUpcomingScheduledPost(post) &&
          (post.account === form.selectedAccount ||
            (!post.account && selectedAccount?.default))
      ),
    [posts, form.selectedAccount, selectedAccount]
  );
  const scheduledPosts = useMemo(
    () =>
      posts.filter(
        (post) =>
          isUpcomingScheduledPost(post) &&
          (post.account === form.selectedAccount ||
            (!post.account && selectedAccount?.default))
      ),
    [posts, form.selectedAccount, selectedAccount]
  );

  const canSubmit =
    Boolean(form.selectedAccount) &&
    accountMissingKeys.length === 0 &&
    form.platforms.length > 0 &&
    (form.caption.trim() || form.media) &&
    (form.publishMode === "instant" || (Boolean(form.scheduledDate) && Boolean(form.scheduledTime)));

  if (authStatus === "checking") {
    return (
      <>
        <LoadingScreen />
        <ToastStack toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  }

  if (authStatus === "unavailable") {
    return (
      <>
        <LoadingScreen
          message="Cannot verify admin session"
          error={sessionError}
          onRetry={checkSession}
        />
        <ToastStack toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  }

  if (authStatus !== "authenticated") {
    return (
      <>
        <LoginPage onLogin={login} onToast={showToast} />
        <ToastStack toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  }

  const pageTitle =
    route === "posts" ? "Post History" : route === "scheduled" ? "Scheduled Posts" : "Composer";

  return (
    <div className="app-layout">
      <Sidebar
        route={route}
        user={user}
        onNavigate={navigate}
        onLogout={() => setShowLogoutModal(true)}
      />

      <main className="app-shell">
        <header className="top-bar">
          <div>
            <p className="eyebrow">{APP_NAME}</p>
            <h1>{pageTitle}</h1>
          </div>
          {route !== "dashboard" && (
            <button
              className="icon-button"
              type="button"
              onClick={() =>
                loadDashboard(false, {
                  toastMessage:
                    route === "scheduled" ? "Scheduled posts refreshed." : "History refreshed."
                })
              }
              aria-label="Refresh"
            >
              <RefreshCw size={18} />
            </button>
          )}
        </header>

        <AccountSelector
          accounts={accounts}
          selectedAccount={form.selectedAccount}
          onChange={changeAccount}
        />

        {accountMissingKeys.length > 0 && (
          <section className="alert" aria-live="polite">
            <AlertCircle size={18} />
            <div>
              <p>
                {selectedAccount?.label || "Selected account"} env keys are missing in backend/.env.
              </p>
              {accountMissingKeys.map((message) => (
                <p key={message}>{message}</p>
              ))}
            </div>
          </section>
        )}

        {errors.length > 0 && (
          <section className="alert" aria-live="polite">
            <AlertCircle size={18} />
            <div>
              {errors.map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          </section>
        )}

        {route === "posts" ? (
          <HistoryView posts={historyPosts} loading={loading} />
        ) : route === "scheduled" ? (
          <ScheduledView posts={scheduledPosts} loading={loading} />
        ) : (
          <DashboardView
            form={form}
            activePlatforms={activePlatforms}
            previewUrl={previewUrl}
            selectedPlatformLabels={selectedPlatformLabels}
            canSubmit={canSubmit}
            submitting={submitting}
            setForm={setForm}
            updateTextOnly={updateTextOnly}
            updatePlatform={updatePlatform}
            submitPost={submitPost}
          />
        )}
      </main>

      {showLogoutModal && (
        <ConfirmModal
          title="Log out?"
          message="Are you sure you want to end this admin session?"
          confirmLabel="Logout"
          onCancel={() => setShowLogoutModal(false)}
          onConfirm={logout}
        />
      )}
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default App;
