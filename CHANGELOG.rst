=======================================
WALLIX Bastion Collection Release Notes
=======================================

.. contents:: Topics

v1.0.0
======

Release Summary
---------------

First release of wallix.bastion, a rewrite of wallix.pam modeled on the wallix-bastion Terraform provider: one idempotent module per Bastion API object, with check mode and diff support.

New Plugins
-----------

Lookup
~~~~~~

- wallix.bastion.secret - Check out account secrets from a WALLIX Bastion

New Modules
-----------

- wallix.bastion.authorization - Manage authorizations on a WALLIX Bastion
- wallix.bastion.authorization_info - Get authorizations from a WALLIX Bastion
- wallix.bastion.connection_policy - Manage connection policies on a WALLIX Bastion
- wallix.bastion.connection_policy_info - Get connection policies from a WALLIX Bastion
- wallix.bastion.device - Manage devices on a WALLIX Bastion
- wallix.bastion.device_info - Get devices from a WALLIX Bastion
- wallix.bastion.device_localdomain - Manage local domains of a device on a WALLIX Bastion
- wallix.bastion.device_localdomain_account - Manage accounts of a device local domain on a WALLIX Bastion
- wallix.bastion.device_localdomain_account_credential - Manage credentials of a device local domain account on a WALLIX Bastion
- wallix.bastion.device_localdomain_account_credential_info - Get the credentials of a device local domain account from a WALLIX Bastion
- wallix.bastion.device_localdomain_account_info - Get the accounts of a device local domain from a WALLIX Bastion
- wallix.bastion.device_localdomain_info - Get the local domains of a device from a WALLIX Bastion
- wallix.bastion.device_service - Manage services of a device on a WALLIX Bastion
- wallix.bastion.device_service_info - Get the services of a device from a WALLIX Bastion
- wallix.bastion.domain - Manage global domains on a WALLIX Bastion
- wallix.bastion.domain_account - Manage accounts of global domains on a WALLIX Bastion
- wallix.bastion.domain_account_credential - Manage credentials of global domain accounts on a WALLIX Bastion
- wallix.bastion.domain_account_credential_info - Get credentials of a global domain account from a WALLIX Bastion
- wallix.bastion.domain_account_info - Get accounts of a global domain from a WALLIX Bastion
- wallix.bastion.domain_info - Get global domains from a WALLIX Bastion
- wallix.bastion.secret - Check out, extend or check in an account password on a WALLIX Bastion
- wallix.bastion.targetgroup - Manage target groups on a WALLIX Bastion
- wallix.bastion.targetgroup_info - Get target groups from a WALLIX Bastion
- wallix.bastion.timeframe - Manage timeframes on a WALLIX Bastion
- wallix.bastion.timeframe_info - Get timeframes from a WALLIX Bastion
- wallix.bastion.user - Manage users on a WALLIX Bastion
- wallix.bastion.user_info - Get users from a WALLIX Bastion
- wallix.bastion.usergroup - Manage user groups on a WALLIX Bastion
- wallix.bastion.usergroup_info - Get user groups from a WALLIX Bastion
