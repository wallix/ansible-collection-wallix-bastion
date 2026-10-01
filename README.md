# WALLIX Bastion Collection

`wallix.bastion` manages WALLIX Bastion objects through the Bastion REST API, with one module per
object type. It follows the [`wallix/wallix-bastion` Terraform provider](https://github.com/wallix/terraform-provider-wallix-bastion):
same objects, same field names, same connection settings and environment variables.

Every module:

- only changes what differs from the Bastion, and reports `changed` accordingly;
- supports `--check` and `--diff`;
- leaves unset options untouched on the Bastion.

## Requirements

- ansible-core 2.16 or later
- Python 3.9 or later on the host running the modules (usually the controller)
- WALLIX Bastion with REST API v3.8 or v3.12

## Installation

```bash
ansible-galaxy collection install wallix.bastion
```

## Connecting

Set the connection once per play with `module_defaults`:

```yaml
- hosts: localhost
  gather_facts: false
  module_defaults:
    group/wallix.bastion.bastion:
      bastion_host: bastion.example.com
      bastion_user: admin
      bastion_token: "{{ vault_bastion_api_key }}"
  tasks:
    - name: Declare a server
      wallix.bastion.device:
        device_name: srv-linux-01
        host: 10.0.0.11
```

Or with the Terraform provider's environment variables:

| Option | Environment variable | Default |
|---|---|---|
| `bastion_host` | `WALLIX_BASTION_HOST` | |
| `bastion_port` | `WALLIX_BASTION_PORT` | `443` |
| `bastion_user` | `WALLIX_BASTION_USER` | |
| `bastion_password` | `WALLIX_BASTION_PASSWORD` | |
| `bastion_token` | `WALLIX_BASTION_TOKEN` | |
| `api_version` | `WALLIX_BASTION_API_VERSION` | `v3.12` |
| `validate_certs` | `WALLIX_BASTION_VALIDATE_CERTS`, or the inverse of `WALLIX_INSECURE_SKIP_VERIFY` | `true` |
| `csrf_enabled` | `WALLIX_CSRF_ENABLED` | `true` |

## Modules

| Object | Module | Read-only module | Terraform equivalent |
|---|---|---|---|
| Devices | `wallix.bastion.device` | `wallix.bastion.device_info` | `wallix-bastion_device` |
| Services of a device | `wallix.bastion.device_service` | `wallix.bastion.device_service_info` | `wallix-bastion_device_service` |
| Local domains of a device | `wallix.bastion.device_localdomain` | `wallix.bastion.device_localdomain_info` | `wallix-bastion_device_localdomain` |
| Accounts of a device local domain | `wallix.bastion.device_localdomain_account` | `wallix.bastion.device_localdomain_account_info` | `wallix-bastion_device_localdomain_account` |
| Password or SSH key of a device account | `wallix.bastion.device_localdomain_account_credential` | `wallix.bastion.device_localdomain_account_credential_info` | `wallix-bastion_device_localdomain_account_credential` |
| Global domains | `wallix.bastion.domain` | `wallix.bastion.domain_info` | `wallix-bastion_domain` |
| Accounts of a global domain | `wallix.bastion.domain_account` | `wallix.bastion.domain_account_info` | `wallix-bastion_domain_account` |
| Password or SSH key of a global domain account | `wallix.bastion.domain_account_credential` | `wallix.bastion.domain_account_credential_info` | `wallix-bastion_domain_account_credential` |
| Users | `wallix.bastion.user` | `wallix.bastion.user_info` | `wallix-bastion_user` |
| User groups | `wallix.bastion.usergroup` | `wallix.bastion.usergroup_info` | `wallix-bastion_usergroup` |
| Target groups | `wallix.bastion.targetgroup` | `wallix.bastion.targetgroup_info` | `wallix-bastion_targetgroup` |
| Authorizations between a user group and a target group | `wallix.bastion.authorization` | `wallix.bastion.authorization_info` | `wallix-bastion_authorization` |
| Timeframes | `wallix.bastion.timeframe` | `wallix.bastion.timeframe_info` | `wallix-bastion_timeframe` |
| Connection policies | `wallix.bastion.connection_policy` | `wallix.bastion.connection_policy_info` | `wallix-bastion_connection_policy` |

Secrets:

| Plugin | Use |
|---|---|
| `wallix.bastion.secret` (module) | Check out, extend or check in an account's password or SSH key |
| `wallix.bastion.secret` (lookup) | Read an account's secret inline, e.g. `{{ lookup('wallix.bastion.secret', 'root@local@srv-01') }}` |

Set `no_log: true` on tasks that check out secrets: a module cannot hide its own output.

Run `ansible-doc wallix.bastion.<module>` for the options of each module.

## Development

```bash
# The collection must live under ansible_collections/wallix/bastion/
ansible-test sanity --docker
ansible-test units --docker
ansible-lint
```

Integration tests run against a real Bastion and are not part of CI:

```bash
cp tests/integration/integration_config.yml.template tests/integration/integration_config.yml  # then edit it
ansible-test integration --allow-destructive --allow-unsupported
```

They create objects named `ansible-test-*` and delete them when done.

Changes go in `changelogs/fragments/` (see [antsibull-changelog](https://github.com/ansible-community/antsibull-changelog)).

## License

GNU General Public License v3.0 or later. See [COPYING](COPYING).
