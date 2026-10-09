
# HealthResponse


## Properties

Name | Type
------------ | -------------
`status` | string
`database` | string
`service` | string
`version` | string
`justTcgConfigured` | boolean
`ebayPricingMode` | string
`ebayDirectEnabled` | boolean
`ebayDirectSessionConfigured` | boolean
`ebayPriceCacheTtlHours` | number

## Example

```typescript
import type { HealthResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "database": null,
  "service": null,
  "version": null,
  "justTcgConfigured": null,
  "ebayPricingMode": null,
  "ebayDirectEnabled": null,
  "ebayDirectSessionConfigured": null,
  "ebayPriceCacheTtlHours": null,
} satisfies HealthResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HealthResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


