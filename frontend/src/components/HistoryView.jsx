import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { platformStyles } from "../constants";
import { mediaTypeForPost } from "../utils";
import PostItem from "./PostItem";

const postMatchesDate = (post, date) => {
  if (!date) {
    return true;
  }

  return new Date(post.createdAt).toISOString().slice(0, 10) === date;
};

const postMatchesPlatform = (post, platform) => {
  if (!platform) {
    return true;
  }

  return post.results.some(
    (result) => result.platform === platform && ["dry_run", "published"].includes(result.status)
  );
};

const postMatchesSearch = (post, search) => {
  if (!search.trim()) {
    return true;
  }

  const value = search.trim().toLowerCase();
  return [
    post.caption,
    post.media?.originalName,
    ...post.results.map((result) => result.message),
    ...post.results.map((result) => platformStyles[result.platform]?.name || result.platform)
  ]
    .filter(Boolean)
    .some((item) => item.toLowerCase().includes(value));
};

function HistoryView({ posts, loading }) {
  const [filters, setFilters] = useState({
    date: "",
    platform: "",
    mediaType: "",
    search: ""
  });

  const filteredPosts = useMemo(
    () =>
      posts.filter(
        (post) =>
          postMatchesDate(post, filters.date) &&
          postMatchesPlatform(post, filters.platform) &&
          (!filters.mediaType || mediaTypeForPost(post) === filters.mediaType) &&
          postMatchesSearch(post, filters.search)
      ),
    [posts, filters]
  );

  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  return (
    <section className="history standalone-history">
      <div className="panel-heading">
        <h2>Post history</h2>
        <span>{loading ? "Loading" : `${filteredPosts.length} of ${posts.length} saved`}</span>
      </div>

      <div className="filter-bar">
        <label className="search-field">
          <Search size={17} />
          <input
            type="search"
            value={filters.search}
            onChange={(event) => updateFilter("search", event.target.value)}
            placeholder="Search posts"
          />
        </label>
        <input
          className="text-input"
          type="date"
          value={filters.date}
          onChange={(event) => updateFilter("date", event.target.value)}
        />
        <select
          className="text-input"
          value={filters.platform}
          onChange={(event) => updateFilter("platform", event.target.value)}
        >
          <option value="">All platforms</option>
          {Object.entries(platformStyles).map(([key, platform]) => (
            <option key={key} value={key}>
              {platform.name}
            </option>
          ))}
        </select>
        <select
          className="text-input"
          value={filters.mediaType}
          onChange={(event) => updateFilter("mediaType", event.target.value)}
        >
          <option value="">All media</option>
          <option value="photo">Photos</option>
          <option value="video">Videos</option>
          <option value="text">Text only</option>
        </select>
      </div>

      <div className="history-list">
        {filteredPosts.length === 0 && !loading ? (
          <p className="empty-history">No posts found.</p>
        ) : (
          filteredPosts.map((post) => <PostItem key={post.id} post={post} />)
        )}
      </div>
    </section>
  );
}

export default HistoryView;
