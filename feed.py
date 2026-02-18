import redis
import json
import datetime

# === CONFIGURATION ===
REDIS_HOST = "localhost"
REDIS_PORT = 6379
feed_cache = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

class FeedManager:
    """
    Manages user feeds using Hybrid Push/Pull architecture.
    - Push (Fan-out-on-write): For regular users, push post ID to all followers' timelines.
    - Pull (Fan-in-on-read): For celebrities (high followers), pull their posts at read time.
    """
    
    CELEBRITY_THRESHOLD = 5000  # Users with >5k followers are 'celebrities'

    def __init__(self):
        pass

    def create_post(self, user_id, content, followers_count, follower_ids):
        """
        Handles post creation and feed distribution.
        """
        post_id = self._save_post_to_db(user_id, content) # Mock DB call
        
        # Decision: Push vs Pull
        if followers_count > self.CELEBRITY_THRESHOLD:
            # PULL STRATEGY: Don't push to millions. Just save.
            print(f"🌟 [CELEB] User {user_id} posted {post_id}. Using Pull-on-Read.")
            # (Followers will query this user's posts when they load their feed)
        else:
            # PUSH STRATEGY: Fan-out to all followers
            print(f"📨 [PUSH] User {user_id} posted {post_id}. Fanning out to {len(follower_ids)} timelines.")
            self._fan_out_to_followers(post_id, follower_ids)
            
        return post_id

    def get_feed(self, user_id, following_ids_map):
        """
        Constructs the feed for a user.
        following_ids_map: dict {following_id: is_celebrity_bool}
        """
        # 1. Get Pushed posts (from Redis timeline)
        timeline_key = f"timeline:{user_id}"
        pushed_posts = feed_cache.lrange(timeline_key, 0, 99) # Get top 100
        
        feed_items = [{"source": "timeline", "post_id": pid} for pid in pushed_posts]
        
        # 2. Get Pulled posts (from Celebrities)
        for following_id, is_celeb in following_ids_map.items():
            if is_celeb:
                # Mock querying recent posts for this celeb
                celeb_posts = self._get_recent_posts_mock(following_id) 
                feed_items.extend(celeb_posts)
                
        # 3. Sort/Rank (Simple Time-based merge for now)
        # In production: Use rank_score from feed_cache table
        print(f"📲 [FEED] Constructed feed for User {user_id} with {len(feed_items)} items.")
        return feed_items

    # --- Internal Helpers ---
    def _save_post_to_db(self, user_id, content):
        # Mocking DB save returning a unique ID
        return f"post_{user_id}_{int(datetime.datetime.now().timestamp())}"

    def _fan_out_to_followers(self, post_id, follower_ids):
        """Push post_id to each follower's Redis list."""
        pipe = feed_cache.pipeline()
        for fid in follower_ids:
            pipe.lpush(f"timeline:{fid}", post_id)
            pipe.ltrim(f"timeline:{fid}", 0, 499) # Keep last 500
        pipe.execute()
        
    def _get_recent_posts_mock(self, user_id):
        return [{"source": "celeb_pull", "post_id": f"post_{user_id}_recent"}]

# === USAGE EXAMPLE ===
if __name__ == "__main__":
    fm = FeedManager()
    
    # 1. Regular user posts (Push)
    fm.create_post(user_id=101, content="Hello World!", followers_count=50, follower_ids=[201, 202, 203])
    
    # 2. Celebrity posts (Pull)
    fm.create_post(user_id=999, content="I am famous.", followers_count=100000, follower_ids=[])
    
    # 3. User 201 reads feed (Follows 101 and 999)
    feed = fm.get_feed(user_id=201, following_ids_map={101: False, 999: True})
