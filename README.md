# rtl_433 Home Assistant app

This fork contains one rtl_433 app (formerly called an add-on). It receives wireless sensor data and can publish it to MQTT. See the [app documentation](rtl_433/README.md), including its Fork Notes, for configuration and differences from the source repository.

Add `https://github.com/SRGDamia1/rtl_433-hass-addons` to the Home Assistant app store's repositories. See [Home Assistant's repository instructions](https://www.home-assistant.io/common-tasks/os/#installing-third-party-apps). This app supports Home Assistant OS on `amd64` and `aarch64`.

## Development

Clone this repository into the local `/addons` directory, reload the app store, and install the local app. Rebuild after changing the Dockerfile or runtime script. See the [Home Assistant app tutorial](https://developers.home-assistant.io/docs/apps/tutorial/).

The Dockerfile uses `ghcr.io/home-assistant/base:3.24` directly. Current Supervisor builds use BuildKit and ignore legacy `build.json` files. To override the rtl_433 revision for a manual build, supply `--build-arg rtl433GitRevision=<tag-or-commit>`.

## Release process

The build workflow checks pull requests and pushes to `main` on native `amd64` and `aarch64` runners. It checks runtime syntax, compiles the container, and checks the installed binary and libraries. These events do not publish images.

1. Update `rtl_433/config.json` and `rtl_433/CHANGELOG.md` for a release.
2. Publish a GitHub release with a tag exactly matching the app version (for example, `0.7.0`).
3. The workflow builds and signs per-architecture images and publishes the signed manifest `ghcr.io/srgdamia1/rtl_433-upd:<version>` using `GITHUB_TOKEN`. No personal access token is needed.
4. Verify that the manifest is public and contains both supported architectures before adding `"image": "ghcr.io/srgdamia1/rtl_433-upd"` to `config.json`. The app currently builds locally on installation. Switching an existing locally built installation to a prebuilt image can require uninstalling and reinstalling; save its options and templates first.

For reproducible releases, pin `rtl433GitRevision` to a tag or commit. A moving branch can change between builds and Docker can reuse a cached clone; a rebuild alone does not guarantee a fresh upstream checkout. See [Home Assistant's publishing guidance](https://developers.home-assistant.io/docs/apps/publishing/).
