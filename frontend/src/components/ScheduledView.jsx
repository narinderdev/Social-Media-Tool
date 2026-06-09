import PostItem from "./PostItem";

function ScheduledView({ posts, loading }) {
  return (
    <section className="history standalone-history">
      <div className="panel-heading">
        <h2>Upcoming scheduled posts</h2>
        <span>{loading ? "Loading" : `${posts.length} upcoming`}</span>
      </div>

      <div className="history-list">
        {posts.length === 0 && !loading ? (
          <p className="empty-history">No upcoming scheduled posts.</p>
        ) : (
          posts.map((post) => <PostItem key={post.id} post={post} />)
        )}
      </div>
    </section>
  );
}

export default ScheduledView;
