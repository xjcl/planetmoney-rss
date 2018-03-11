# planetmoney-rss

**The feed is available under this link**:
    https://xjcl.github.io/planetmoney-rss/npr_pm_feed.xml

Planetmoney-rss is a script to assemble a podcast feed containing **ALL** Planet Money episodes, including all old episodes going back to 2008.
Their [official feed](https://itunes.apple.com/us/podcast/planet-money/id290783428?mt=2) only includes the most recent 300 episodes due to an iTunes limitation.

This is done by downloading the human-interfacing HTML from NPR's Planet Money website, parsing it into [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) datatypes (PlanetMoneyHTMLParser), and emitting an XML RSS feed.

For more information look at this reddit thread:
    https://www.reddit.com/r/nprplanetmoney/comments/5jl8tq/why_does_the_podcast_feed_end_at_464_can_someone/


Example of how this feed looks in Podcast Addict:

![im1](https://i.imgur.com/lwupMH9.png)

![im2](https://i.imgur.com/SanFKcv.png)

![im3](https://i.imgur.com/5qTZGQb.png)
