# Contributing Guidelines

We love improvements to our tools! EDGI has general [guidelines for contributing][edgi-contributing] and a [code of conduct][edgi-conduct] for all of our organizational repos.

## Here are some notes specific to this project:

* We have configured this project on CircleCI to [only run on pull
  requests and `master` branch][pr-config]– so if you PR from a fork, the Circle CI build will fail! Please PR from a branch instead (you will need permissions).
* We have further configured CircleCI to **NOT** delete videos from Zoom on runs related to pull requests. (As mentioned in README, videos are normally deleted after upload.)

<!-- Links -->
[edgi-conduct]: https://github.com/edgi-govdata-archiving/overview/blob/master/CONDUCT.md
[edgi-contributing]: https://github.com/edgi-govdata-archiving/overview/blob/master/CONTRIBUTING.md
[pr-config]: docs/screenshot-circleci-only-prs.png
