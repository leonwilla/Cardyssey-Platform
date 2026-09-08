
# CreateMarketplaceOfferRequest


## Properties

Name | Type
------------ | -------------
`listingId` | string
`quantity` | number
`priceEur` | number
`message` | string

## Example

```typescript
import type { CreateMarketplaceOfferRequest } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "listingId": null,
  "quantity": null,
  "priceEur": null,
  "message": null,
} satisfies CreateMarketplaceOfferRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreateMarketplaceOfferRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


