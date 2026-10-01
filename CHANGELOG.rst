=======================================
WALLIX Bastion Collection Release Notes
=======================================

.. contents:: Topics

v1.1.0
======

Release Summary
---------------

Complete coverage of the wallix-bastion Terraform provider: a module for every resource and an ``_info`` module for every data source.

Breaking Changes / Porting Guide
--------------------------------

- The connection option ``timeout`` (HTTP timeout of each request to the Bastion API) is renamed ``bastion_timeout``, like the other connection options. The name ``timeout`` is now free for the API field of the same name, for example in ``wallix.bastion.externalauth_ldap``.

New Modules
-----------

- wallix.bastion.apikey - Manage API keys on a WALLIX Bastion
- wallix.bastion.apikey_info - Get API keys from a WALLIX Bastion
- wallix.bastion.apikey_v2 - Manage API keys with a profile on a WALLIX Bastion
- wallix.bastion.apikey_v2_info - Get API keys from a WALLIX Bastion, with their profile
- wallix.bastion.application - Manage applications on a WALLIX Bastion
- wallix.bastion.application_info - Get applications from a WALLIX Bastion
- wallix.bastion.application_localdomain - Manage local domains of an application on a WALLIX Bastion
- wallix.bastion.application_localdomain_account - Manage accounts of an application local domain on a WALLIX Bastion
- wallix.bastion.application_localdomain_account_credential - Manage the password of an application local domain account on a WALLIX Bastion
- wallix.bastion.application_localdomain_account_credential_info - Get the credentials of an application local domain account from a WALLIX Bastion
- wallix.bastion.application_localdomain_account_info - Get the accounts of an application local domain from a WALLIX Bastion
- wallix.bastion.application_localdomain_info - Get the local domains of an application from a WALLIX Bastion
- wallix.bastion.authdomain_ad - Manage Active Directory authentication domains on a WALLIX Bastion
- wallix.bastion.authdomain_ad_info - Get Active Directory authentication domains from a WALLIX Bastion
- wallix.bastion.authdomain_azuread - Manage Microsoft Entra ID (Azure AD) authentication domains on a WALLIX Bastion
- wallix.bastion.authdomain_azuread_info - Get Microsoft Entra ID (Azure AD) authentication domains from a WALLIX Bastion
- wallix.bastion.authdomain_ldap - Manage LDAP authentication domains on a WALLIX Bastion
- wallix.bastion.authdomain_ldap_info - Get LDAP authentication domains from a WALLIX Bastion
- wallix.bastion.authdomain_mapping - Map directory groups to user groups on a WALLIX Bastion
- wallix.bastion.authdomain_mapping_info - Get the group mappings of an authentication domain from a WALLIX Bastion
- wallix.bastion.authdomain_saml - Manage SAML authentication domains on a WALLIX Bastion
- wallix.bastion.authdomain_saml_info - Get SAML authentication domains from a WALLIX Bastion
- wallix.bastion.certificate_authority - Manage certificate authorities on a WALLIX Bastion
- wallix.bastion.certificate_authority_info - Get certificate authorities from a WALLIX Bastion
- wallix.bastion.checkout_policy - Manage checkout policies on a WALLIX Bastion
- wallix.bastion.checkout_policy_info - Get checkout policies from a WALLIX Bastion
- wallix.bastion.cluster - Manage clusters on a WALLIX Bastion
- wallix.bastion.cluster_info - Get clusters from a WALLIX Bastion
- wallix.bastion.config_smtp - Manage the SMTP configuration of a WALLIX Bastion
- wallix.bastion.config_smtp_info - Get the SMTP configuration of a WALLIX Bastion
- wallix.bastion.config_wsm - Manage the Web Session Manager configuration of a WALLIX Bastion
- wallix.bastion.config_wsm_info - Get the Web Session Manager configuration of a WALLIX Bastion
- wallix.bastion.config_x509 - Manage the X.509 configuration of a WALLIX Bastion
- wallix.bastion.config_x509_info - Get the X.509 configuration of a WALLIX Bastion
- wallix.bastion.configoption_info - Get configuration options from a WALLIX Bastion
- wallix.bastion.connection_message - Set the connection messages of a WALLIX Bastion
- wallix.bastion.connection_message_info - Get the connection messages of a WALLIX Bastion
- wallix.bastion.encryption - Set up or change the encryption passphrase of a WALLIX Bastion
- wallix.bastion.encryption_info - Get the encryption state of a WALLIX Bastion
- wallix.bastion.externalauth_kerberos - Manage Kerberos external authentications on a WALLIX Bastion
- wallix.bastion.externalauth_kerberos_info - Get Kerberos external authentications from a WALLIX Bastion
- wallix.bastion.externalauth_ldap - Manage LDAP external authentications on a WALLIX Bastion
- wallix.bastion.externalauth_ldap_info - Get LDAP external authentications from a WALLIX Bastion
- wallix.bastion.externalauth_radius - Manage RADIUS external authentications on a WALLIX Bastion
- wallix.bastion.externalauth_radius_info - Get RADIUS external authentications from a WALLIX Bastion
- wallix.bastion.externalauth_saml - Manage SAML external authentications on a WALLIX Bastion
- wallix.bastion.externalauth_saml_info - Get SAML external authentications from a WALLIX Bastion
- wallix.bastion.externalauth_tacacs - Manage TACACS+ external authentications on a WALLIX Bastion
- wallix.bastion.externalauth_tacacs_info - Get TACACS+ external authentications from a WALLIX Bastion
- wallix.bastion.local_password_policy_info - Get local password policies from a WALLIX Bastion
- wallix.bastion.notification - Manage notifications on a WALLIX Bastion
- wallix.bastion.notification_info - Get notifications from a WALLIX Bastion
- wallix.bastion.passwordchangepolicy - Manage password change policies on a WALLIX Bastion
- wallix.bastion.passwordchangepolicy_info - Get password change policies from a WALLIX Bastion
- wallix.bastion.profile - Manage user profiles on a WALLIX Bastion
- wallix.bastion.profile_info - Get user profiles from a WALLIX Bastion
- wallix.bastion.version_info - Get the version of a WALLIX Bastion

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
