# WALLIX Bastion Collection

`wallix.bastion` manages WALLIX Bastion objects through the Bastion REST API, with one module per
object type. It follows the [`wallix/wallix-bastion` Terraform provider](https://github.com/wallix/terraform-provider-wallix-bastion):
same objects, same field names, same connection settings and environment variables.
Where the real API differs from the provider's documentation, the modules follow the API and their
documentation says so.

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
| `bastion_timeout` | | `30` |

## Modules

Every resource and data source of the Terraform provider has a module: `wallix.bastion.<name>` for
the resource `wallix-bastion_<name>` and `wallix.bastion.<name>_info` for the data source.

### Devices

| Module | Read-only module | Description |
|---|---|---|
| `device` | `device_info` | Manage devices on a WALLIX Bastion |
| `device_service` | `device_service_info` | Manage services of a device on a WALLIX Bastion |
| `device_localdomain` | `device_localdomain_info` | Manage local domains of a device on a WALLIX Bastion |
| `device_localdomain_account` | `device_localdomain_account_info` | Manage accounts of a device local domain on a WALLIX Bastion |
| `device_localdomain_account_credential` | `device_localdomain_account_credential_info` | Manage credentials of a device local domain account on a WALLIX Bastion |

### Applications

| Module | Read-only module | Description |
|---|---|---|
| `application` | `application_info` | Manage applications on a WALLIX Bastion |
| `application_localdomain` | `application_localdomain_info` | Manage local domains of an application on a WALLIX Bastion |
| `application_localdomain_account` | `application_localdomain_account_info` | Manage accounts of an application local domain on a WALLIX Bastion |
| `application_localdomain_account_credential` | `application_localdomain_account_credential_info` | Manage the password of an application local domain account on a WALLIX Bastion |

### Global domains

| Module | Read-only module | Description |
|---|---|---|
| `domain` | `domain_info` | Manage global domains on a WALLIX Bastion |
| `domain_account` | `domain_account_info` | Manage accounts of global domains on a WALLIX Bastion |
| `domain_account_credential` | `domain_account_credential_info` | Manage credentials of global domain accounts on a WALLIX Bastion |

### Users and access

| Module | Read-only module | Description |
|---|---|---|
| `user` | `user_info` | Manage users on a WALLIX Bastion |
| `usergroup` | `usergroup_info` | Manage user groups on a WALLIX Bastion |
| `targetgroup` | `targetgroup_info` | Manage target groups on a WALLIX Bastion |
| `authorization` | `authorization_info` | Manage authorizations on a WALLIX Bastion |
| `profile` | `profile_info` | Manage user profiles on a WALLIX Bastion |
| `timeframe` | `timeframe_info` | Manage timeframes on a WALLIX Bastion |

### Policies

| Module | Read-only module | Description |
|---|---|---|
| `connection_policy` | `connection_policy_info` | Manage connection policies on a WALLIX Bastion |
| `checkout_policy` | `checkout_policy_info` | Manage checkout policies on a WALLIX Bastion |
| `passwordchangepolicy` | `passwordchangepolicy_info` | Manage password change policies on a WALLIX Bastion |

### Authentication

| Module | Read-only module | Description |
|---|---|---|
| `authdomain_ad` | `authdomain_ad_info` | Manage Active Directory authentication domains on a WALLIX Bastion |
| `authdomain_azuread` | `authdomain_azuread_info` | Manage Microsoft Entra ID (Azure AD) authentication domains on a WALLIX Bastion |
| `authdomain_ldap` | `authdomain_ldap_info` | Manage LDAP authentication domains on a WALLIX Bastion |
| `authdomain_saml` | `authdomain_saml_info` | Manage SAML authentication domains on a WALLIX Bastion |
| `authdomain_mapping` | `authdomain_mapping_info` | Map directory groups to user groups on a WALLIX Bastion |
| `externalauth_kerberos` | `externalauth_kerberos_info` | Manage Kerberos external authentications on a WALLIX Bastion |
| `externalauth_ldap` | `externalauth_ldap_info` | Manage LDAP external authentications on a WALLIX Bastion |
| `externalauth_radius` | `externalauth_radius_info` | Manage RADIUS external authentications on a WALLIX Bastion |
| `externalauth_saml` | `externalauth_saml_info` | Manage SAML external authentications on a WALLIX Bastion |
| `externalauth_tacacs` | `externalauth_tacacs_info` | Manage TACACS+ external authentications on a WALLIX Bastion |

### API keys

| Module | Read-only module | Description |
|---|---|---|
| `apikey` | `apikey_info` | Manage API keys on a WALLIX Bastion |
| `apikey_v2` | `apikey_v2_info` | Manage API keys with a profile on a WALLIX Bastion |

### Appliance

| Module | Read-only module | Description |
|---|---|---|
| `cluster` | `cluster_info` | Manage clusters on a WALLIX Bastion |
| `certificate_authority` | `certificate_authority_info` | Manage certificate authorities on a WALLIX Bastion |
| `notification` | `notification_info` | Manage notifications on a WALLIX Bastion |
| `connection_message` | `connection_message_info` | Set the connection messages of a WALLIX Bastion |
| `config_smtp` | `config_smtp_info` | Manage the SMTP configuration of a WALLIX Bastion |
| `config_wsm` | `config_wsm_info` | Manage the Web Session Manager configuration of a WALLIX Bastion |
| `config_x509` | `config_x509_info` | Manage the X.509 configuration of a WALLIX Bastion |
| `encryption` | `encryption_info` | Set up or change the encryption passphrase of a WALLIX Bastion |

### Read-only

| Module | Description |
|---|---|
| `configoption_info` | Get configuration options from a WALLIX Bastion |
| `local_password_policy_info` | Get local password policies from a WALLIX Bastion |
| `version_info` | Get the version of a WALLIX Bastion |

Secrets:

| Plugin | Use |
|---|---|
| `wallix.bastion.secret` (module) | Check out, extend or check in an account's password or SSH key |
| `wallix.bastion.secret` (lookup) | Read an account's secret inline, e.g. `{{ lookup('wallix.bastion.secret', 'root@local@srv-01') }}` |

Set `no_log: true` on tasks that check out secrets: a module cannot hide its own output.

The [documentation](docs/README.md) has a page per module with its options, examples and return
values; `ansible-doc wallix.bastion.<module>` shows the same.

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
