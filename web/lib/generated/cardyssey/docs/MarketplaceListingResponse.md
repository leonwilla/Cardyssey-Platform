
# MarketplaceListingResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`sellerFriendCode` | string
`sellerDisplayName` | string
`cardId` | string
`languageCode` | string
`name` | string
`setName` | string
`localId` | string
`imageBase` | string
`variant` | string
`condition` | string
`quantity` | number
`priceEur` | number
`negotiable` | boolean

## Example

```typescript
import type { MarketplaceListingResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "sellerFriendCode": null,
  "sellerDisplayName": null,
  "cardId": null,
  "languageCode": null,
  "name": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "variant": null,
  "condition": null,
  "quantity": null,
  "priceEur": null,
  "negotiable": null,
} satisfies MarketplaceListingResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MarketplaceListingResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


