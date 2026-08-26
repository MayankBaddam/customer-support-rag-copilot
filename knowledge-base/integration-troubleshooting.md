# CloudDesk Integration Troubleshooting

**Document ID:** KB-INTEGRATIONS-001  
**Version:** 1.0  
**Effective date:** 2026-01-15  
**Status:** Active

## Connection checklist

Before troubleshooting an integration, confirm that the workspace is on a plan that includes the integration, the connector is enabled, and the workspace owner completed the authorization flow.

## Common symptoms

### `AUTH-401`

The integration authorization has expired or was revoked. Reconnect the integration from **Settings > Integrations**. Do not ask the customer to send an access token or secret.

### `RATE-429`

The connected service has temporarily limited requests. Wait for the provider limit to reset, then retry with a smaller operation. Repeated limits should be escalated with the approximate time and operation type.

### `SYNC-504`

The provider did not respond before the request timed out. Confirm the provider status, retry once, and record the affected operation if the timeout continues.

## Escalation details

Include the integration name, error code, approximate timestamp, and whether the issue affects one workspace or many. Exclude credentials, tokens, customer content, and unnecessary personal data.

## Safety

CloudDesk support cannot bypass a provider's authorization, rate limit, or security controls. Never disable verification to make a connection succeed.
