Introduction
============

The Student Robotics Competition Software, or *SRComp*, is a suite of software
for running competition events. It aims to record the entire state of the
competition in a single place and provide tooling for working with that data in
a consistent and reproducible manner.

SRComp assumes:
 * that you have a league section and/or a knockout section; if you have both
   then the league comes first and seeds the knockout
 * that you can generate fair match plan (i.e: who plays who in which match)
   yourself (though it does provide some tooling to *check* that a plan is fair)

SRComp includes support for:
 * generating match schedules from match plans, by incorporating both time to
   reset arenas between matches as well as planned and unexpected delays
 * games with multiple participants, with graceful handling of no-shows and
   disqualifications
 * normalising per-game scores to allocate league scores and/or determine
   knockout progression
 * resolving ties
 * concurrent arenas, though with the caveat that games in multiple arenas start
   at the same time and are of the same length
 * "shepherds"; people who fetch participants before their matches
 * large-screen displays of information for shepherds
 * large-screen displays of information for the audience
 * web pages with information for an external audience
 * web pages with information for competitors
 * real-time updates of the state of the competition, including consistent
   distributed hosting of the displays and HTTP API
