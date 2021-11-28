# Planet Money but it's all episodes

**The feed is available here**:
- https://xjcl.github.io/planetmoney-rss/npr_pm_feed.xml

*Planetmoney-rss* is a repository to assemble a podcast feed containing **ALL** [Planet Money](https://en.wikipedia.org/wiki/Planet_Money) episodes, including all old episodes going back to 2008.
NPR's [official feed](https://itunes.apple.com/us/podcast/planet-money/id290783428?mt=2) only includes the most recent 300 of the show's more-than-1000 episodes due to an iTunes limitation.

All episodes < 2019-05-01 were scraped from NPR's Planet Money [website](https://www.npr.org/sections/money/127413729/podcast/archive) and exported into an XML RSS file using Python code ([`npr_pm_rip.py`](npr_pm_rip.py)). **In 2019, NPR STOPPED updating that site with podcast episodes, so that script is no longer used.**

Episodes >= 2019-05-01 are directly copied from the official NPR feed at https://feeds.npr.org/510289/podcast.xml. This is less work for me and also ensures correct metadata. Needs to be done every 2-3 years before episodes fall off the official feed (should be managable if I don't die). **I now manually run [`wget_feed_HEAD.sh`](wget_feed_HEAD.sh) and then copypaste the appropriate entries into [`npr_pm_feed.xml`](npr_pm_feed.xml).**

----

For more information look at these reddit threads:
- https://www.reddit.com/r/nprplanetmoney/comments/86ot7a/ultimate_guide_to_listening_to_all_old_episodes/
- https://www.reddit.com/r/nprplanetmoney/comments/5jl8tq/why_does_the_podcast_feed_end_at_464_can_someone/

Screenshots of how this feed looks in Podcast Addict:

<img src="https://i.imgur.com/lwupMH9.png" width="270px"> <img src="https://i.imgur.com/SanFKcv.png" width="270px"> <img src="https://i.imgur.com/5qTZGQb.png" width="270px">
