# Adding a module

Each module maps to one resource of the
[Terraform provider](https://github.com/wallix/terraform-provider-wallix-bastion), and each
`_info` module to its data source. Read `bastion/resource_<name>.go` first: it gives the API
path, the JSON fields, which fields are required, `ForceNew` (create-only) and `Sensitive`
(secret), and how the object is looked up by name.

## Files

For a resource `<name>`:

| File | Content |
|---|---|
| `plugins/modules/<name>.py` | The module, built on `BastionModule` and `BastionResource` |
| `plugins/modules/<name>_info.py` | Read-only module, built on `run_info` |
| `tests/unit/plugins/modules/test_<name>.py` | Unit tests against `FakeBastion` |
| `tests/integration/targets/<name>/` | `aliases` (`destructive`, `unsupported`), `tasks/main.yml` with `module_defaults`, `tasks/lifecycle.yml` |
| `meta/runtime.yml` | Add both modules to `action_groups.bastion` |
| `changelogs/fragments/` | Nothing for new modules: antsibull-changelog picks them up from `version_added` |

`plugins/modules/device.py`, `device_info.py`, `tests/unit/plugins/modules/test_device.py` and
`tests/integration/targets/device/` are the reference implementation; copy them.

## Rules

- **Option names are the API field names**, as in the provider (`device_name`, not `name`).
- **No defaults on object fields.** An unset option means "leave as is". Only `state` has a default.
- **Required on create, optional on update**: list such options in `required_on_create`,
  not as `required: true`. Only the name field is `required: true`.
- **`ForceNew` fields go in `create_only_fields`.** The module fails instead of recreating.
- **`Sensitive` fields go in `secret_fields`**, with `no_log: true`, plus an
  `update_password: [always, on_create]` option (default `on_create`) mapped to `update_secrets`.
- **Unordered lists** (sets in the provider) go in `set_fields`.
- **Child objects** (services, local domains, accounts) take the parent's name as an option
  (`device_name`, `domain_name`, ...) and resolve it with `find_parent()`; the resource path is
  then `"devices/%s/services" % parent_id`.
- **List fields**: if PUT without `?force=true` appends to them instead of replacing them (true
  for most objects with lists), set `update_query="force=true"`, like the provider does, and test
  that removing an item really removes it.
- Fields the API refuses in a PUT body (often the name or the protocol) go in `exclude_on_update`.
  If the PUT also refuses fields that GET returns, use `merge_on_update=False` to send only the
  requested fields. `null` values are never sent back.
- Collections without `q=` search (credentials) use `search="list"`.
- Option names that clash with Ansible or with the connection options are the only exception to
  "option names are API field names": `message` is reserved by Ansible (`connection_message` uses
  `message_text`). The connection options all start with `bastion_` (except `api_version`,
  `validate_certs` and `csrf_enabled`) so API fields such as `timeout` keep their name.
- Objects without an `id` (users) are addressed by name: override `object_path()` and `read()`,
  see `plugins/modules/user.py`.
- When the API shape differs from the options (nested objects, ids instead of names, fields the
  API renames), subclass `BastionResource` and override `desired()`, `normalize()` or `body()`.
  Don't change `module_utils` for a single module.
- Every module supports check mode and diff mode, and documents both in `attributes`.
- `RETURN` documents the returned object with a realistic `sample`.
- Docs reference the Terraform equivalent in `description`.

## Tests

Unit tests use `FakeBastion` (`tests/unit/plugins/module_utils/fake_bastion.py`), an in-memory
API. Cover at least: create, create in check mode (no writes), identical re-run (no writes),
partial update keeps unset fields, delete, delete again, and any module-specific rule
(secrets, create-only fields, missing parent).

Integration tests run the same lifecycle against a real Bastion. Name every object
`ansible-test-<random>` and delete it in an `always:` block.

If `pytest-ansible` is installed in your user site-packages, run `ansible-test units` with
`--venv` or `--docker`: the plugin rewrites the collection path and breaks the lookup tests.

```bash
ansible-test sanity --docker
ansible-test units --docker
ansible-test integration <name> --allow-destructive --allow-unsupported
ansible-lint
```
