# planetmoney-rss

**This feed is available here**:
    https://xjcl.github.io/planetmoney-rss/npr_pm_feed.xml

*Planetmoney-rss* is a script to assemble a podcast feed containing **ALL** [Planet Money](https://en.wikipedia.org/wiki/Planet_Money) episodes, including all old episodes going back to 2008.
Their [official feed](https://itunes.apple.com/us/podcast/planet-money/id290783428?mt=2) only includes the most recent 300 of the show's more-than-1000 episodes due to an iTunes limitation.

This is done by downloading the human-interfacing HTML from NPR's Planet Money [website](https://www.npr.org/sections/money/127413729/podcast/archive), parsing it into [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) datatypes (`PlanetMoneyHTMLParser`), and emitting an XML RSS feed. This takes around 30 minutes because every single of the >1000 episode pages have to be downloaded and parsed; only they contain all download links and exact timestamps. The script caches the feed so not all sites have to be re-downloaded when a new episode is released so an update only takes a few seconds.

The feed is titled *Planet Money but it's all episodes*. Currently the pages `npr_pm_test.xml` and `npr_pm_feed.xml` are identical. I will soon deprecate the former's URL which was originally for testing purposes, and the Podcast Addict search should only find the correct URL.

For more information look at these reddit threads:
- https://www.reddit.com/r/nprplanetmoney/comments/86ot7a/ultimate_guide_to_listening_to_all_old_episodes/
- https://www.reddit.com/r/nprplanetmoney/comments/5jl8tq/why_does_the_podcast_feed_end_at_464_can_someone/

Screenshots of how this feed looks in Podcast Addict:

![im1](https://i.imgur.com/lwupMH9.png)

![im2](https://i.imgur.com/SanFKcv.png)

![im3](https://i.imgur.com/5qTZGQb.png)

