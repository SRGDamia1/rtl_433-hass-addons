# rtl_433 configuration

Templates are stored in Home Assistant's `/config/rtl_433/`. Start the app once to create the default `.conf.template`, edit it, then restart. Use one template per radio, setting `device` before `output` lines. The legacy `rtl_433_conf_file` option selects a single file relative to Home Assistant's `/config/`.

* `retain`: controls MQTT retention for templates using `${retain}` (default: enabled).
* `allow_commands`: enables shell execution of JSON strings sent through Supervisor stdin (default: disabled).
* `rtl_433_conf_file`: legacy single-file mode; leave empty to use templates.

Supervisor can supply MQTT broker credentials automatically. For an external broker, enter connection settings in each template. PID and stdin status topics require Supervisor MQTT service settings. Add `output kv` to see sensor data in the logs.

For the web interface, add `output http://0.0.0.0:8433` alongside your MQTT output. Use 8434 for a second radio. The app uses host networking, so these ports must be free on the host. The web UI button uses 8433. The direct HTTP interface is not protected by Home Assistant ingress authentication.

Templates are expanded by Bash and can execute command substitutions. Only use trusted templates. Generated configurations live in the container's private `/tmp/rtl_433/` directory.

See the [full README and Fork Notes](https://github.com/SRGDamia1/rtl_433-hass-addons/blob/main/rtl_433/README.md) for MQTT topic migration and examples.
