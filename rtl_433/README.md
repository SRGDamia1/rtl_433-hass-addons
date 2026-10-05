# rtl_433 Home Assistant Add-on

## Fork Notes

This fork is based on [pbkhrv's rtl_433 (next) add-on](https://github.com/pbkhrv/rtl_433-hass-addons/tree/main/rtl_433-next). It contains one add-on, with the distinct slug `rtl433_upd`; MQTT auto discovery is still supplied separately by the source repository.

Compared with that source add-on:

* Like the source's next add-on, this fork builds rtl_433 from upstream `master`. Each build resolves the current branch commit through BuildKit's Git source support, so new upstream commits invalidate the source cache. Updating the running binary requires rebuilding or reinstalling the app.
* The container uses Home Assistant's multi-architecture Alpine 3.24 base and supports `aarch64` and `amd64`. The Dockerfile supplies its base image and labels directly, following the [current BuildKit guidance](https://developers.home-assistant.io/blog/2026/04/02/builder-migration/).
* Host networking allows rtl_433 HTTP outputs on ports 8433 and 8434, with an **Open Web UI** link for 8433. You must enable HTTP output in a radio template; opening or exposing a port alone does not start the web server.
* Each radio's PID is published as a retained message to `rtl_433/process_id/<template-name>` when Supervisor supplies MQTT service settings. Sensor MQTT outputs remain controlled by your templates.
* Optional Supervisor stdin commands publish input and results to `rtl_433/stdin/input` and `rtl_433/stdin/result`. Set `allow_commands` to `true` to enable this feature; it is disabled by default because it executes shell commands inside the container.
* Radio processes are supervised even when stdin closes. If one radio exits, the app stops the remaining radios and exits with a failure status. Rendered configurations are private temporary files; user `.conf` files are preserved.
* This fork currently builds locally when installed (there is no `image` field). The release workflow can publish signed, versioned multi-architecture images; see the repository README before switching installation to those images.

Installing this fork changes the default MQTT topic prefix because its repository and slug differ. To preserve existing entities, explicitly set the `devices`, `events`, and `states` topic paths in each template to the paths your existing discovery configuration uses. The compatibility example in the generated template uses the source stable add-on's prefix; adjust it for your installation.

## About

This add-on is a simple wrapper around the excellent [rtl_433](https://github.com/merbanan/rtl_433) project that receives wireless sensor data via [one of the supported SDR dongles](https://triq.org/rtl_433/HARDWARE.html), decodes and outputs it in a variety of formats including JSON and MQTT. The wireless sensors rtl_433 understands transmit data mostly on 433.92 MHz, 868 MHz, 315 MHz, 345 MHz, and 915 MHz ISM bands.

[View the rtl_433 documentation](https://triq.org/rtl_433)

## How it works

The only thing this add-on does is run rtl_433 under the Home Assistant OS supervisor. All you have to do is supply a config file.

On first start, the add-on creates a template configured for MQTT using the broker settings supplied by Supervisor. To print received data in the app logs as well, add `output kv` to the template.

Once you get the rtl_433 sensor data into MQTT, you'll need to help Home Assistant discover and make sense of it. You can do that in a number of ways:

  * manually configure `sensors` and `binary_sensors` in HA and [link them to the appropriate MQTT topics](https://www.home-assistant.io/integrations/sensor.mqtt/) coming out of rtl_433,
  * run the [rtl_433_mqtt_hass.py](https://github.com/merbanan/rtl_433/tree/master/examples/rtl_433_mqtt_hass.py) script manually or on a schedule to do most of the configuration automatically, or
  * install the [rtl_433 MQTT Auto Discovery Home Assistant Add-on](https://github.com/pbkhrv/rtl_433-hass-addons/tree/main/rtl_433_mqtt_autodiscovery), which runs rtl_433_mqtt_hass.py for you.

## Prerequisites

 To use this add-on, you need the following:

 1. [An SDR dongle supported by rtl_433](https://triq.org/rtl_433/HARDWARE.html).

 2. Home Assistant OS on an `amd64` or `aarch64` machine with the SDR dongle plugged into it. Home Assistant now calls add-ons **apps**. Home Assistant Container does not include the Supervisor app store.

 3. Some wireless sensors supported by rtl_433. The full list of supported protocols and devices can be found under "Supported device protocols" section of the [rtl_433's README](https://github.com/merbanan/rtl_433/blob/master/README.md).

## Installation

 1. Create an rtl_433 config file that does what you need. It might work better if you do this on a computer other than the one running Home Assistant OS, so that you can experiment freely and iterate until you arrive at a configuration that works well. See below for more details.

 2. Upload the config file into Home Assistant's "/config" directory using whatever method works for you (via Samba add-on, ssh/scp, File Editor add-on etc).

 3. Install the add-on.

 4. Plug your SDR dongle into the machine running the add-on.

 5. Start the addon. A default configuration will be created in `/config/rtl_433/`. To add or edit additional configurations, create multiple `.conf.template` files in that directory.

 6. Restart the add-on after editing templates and check the logs. Templates remain in Home Assistant's `/config/rtl_433/`; rendered files are placed in the container's `/tmp/rtl_433/`.

## Configuration

For a "zero configuration" setup, install the [Mosquitto broker](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md) addon. While other brokers may work, they are not tested and will require manual setup. Once the addon is installed, start or restart the rtl_433 and rtl_433_mqtt_autodiscovery addons to start capturing known 433 MHz protocols.

For more advanced configuration, take a look at the example config file included in the rtl_433 source code: [rtl_433.example.conf](https://github.com/merbanan/rtl_433/blob/master/conf/rtl_433.example.conf)

Note that since the configuration file has bash variables in it, **dollar signs and other special shell characters need to be escaped**. For example, to use the literal string `$GPRMC` in the configuration file, use `\$GPRMC`.

Templates are expanded by Bash, including command substitutions. Treat them as executable configuration and only use trusted templates.

The `retain` option controls if MQTT's `retain` flag is enabled or disabled by default. It can be overridden on a per-radio basis by setting `retain` to `true` or `false` in the `output` setting.

For an external MQTT broker, put connection settings directly in each template. Supervisor MQTT service discovery is optional; without it, the separate PID and stdin status messages are not published.

### Web interface

Add this alongside your existing MQTT output in one radio's `.conf.template` file:

```text
output http://0.0.0.0:8433
```

Restart the app, then open `http://<Home Assistant host>:8433`. For another radio, use 8434 or another free port. Host networking means ports are selected in the templates and cannot be remapped in the app's Network settings. The **Open Web UI** button always uses 8433. This direct HTTP interface has no Home Assistant ingress authentication; keep access within your trusted network.

### Supervisor stdin commands

Enable `allow_commands` only if your automations need shell execution, then send a JSON string through the Supervisor stdin action, for example `"kill -USR1 <PID>"`. The PID can be obtained from the retained process topic. JSON objects and other non-string inputs are rejected. Legacy `rtl_433_conf_file` mode runs a single file directly and does not provide the PID or stdin features.

When configuring manually, assuming that you intend to get the rtl_433 data into Home Assistant, the absolute minimum that you need to specify in the config file is the [MQTT connection and authentication information](https://triq.org/rtl_433/OPERATION.html#mqtt-output):

```
output      mqtt://HOST:PORT,user=XXXX,pass=YYYYYYY
```

rtl_433 defaults to listening on 433.92MHz, but even if that's what you need, it's probably a good idea to specify the frequency explicitly to avoid confusion:

```
frequency   433.92M
```

You might also want to narrow down the list of protocols that rtl_433 should try to decode. The full list can be found under "Supported device protocols" section of the [README](https://github.com/merbanan/rtl_433/blob/master/README.md). Let's say you want to listen to Acurite 592TXR temperature/humidity sensors:

```
protocol    40
```

Last but not least, if you decide to use the MQTT auto discovery script or add-on, its documentation recommends converting units in all of the data coming out of rtl_433 into SI:

```
convert     si
```

Assuming you have only one USB dongle attached and rtl_433 is able to automatically find it, we arrive at a minimal rtl_433 config file that looks like this:

```
output      mqtt://HOST:PORT,user=XXXX,pass=YYYYYYY

frequency   433.92M
protocol    40

convert     si
```

Please check [the official rtl_433 documentation](https://triq.org/rtl_433) and [config file examples](https://github.com/merbanan/rtl_433/tree/master/conf) for more information.

## Credit

This add-on is based on James Fry's [rtl4332mqtt Hass.IO Add-on](https://github.com/james-fry/hassio-addons/tree/master/rtl4332mqtt), which is in turn based on Chris Kacerguis' project here: [https://github.com/chriskacerguis/honeywell2mqtt](https://github.com/chriskacerguis/honeywell2mqtt), which is in turn based on Marco Verleun's rtl2mqtt image here: [https://github.com/roflmao/rtl2mqtt](https://github.com/roflmao/rtl2mqtt).
