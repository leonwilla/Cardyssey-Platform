
# MarketplaceOfferResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`listingId` | string
`buyerFriendCode` | string
`buyerDisplayName` | string
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
`offerPriceEur` | number
`listingPriceEur` | number
`message` | string
`status` | string
`createdAt` | string
`updatedAt` | string

## Example

```typescript
import type { MarketplaceOfferResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "listingId": null,
  "buyerFriendCode": null,
  "buyerDisplayName": null,
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
  "offerPriceEur": null,
  "listingPriceEur": null,
  "message": null,
  "status": null,
  "createdAt": null,
  "updatedAt": null,
} satisfies MarketplaceOfferResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MarketplaceOfferResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


