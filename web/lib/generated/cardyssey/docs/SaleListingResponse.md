
# SaleListingResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`collectionItemId` | string
`cardId` | string
`name` | string
`setName` | string
`localId` | string
`imageBase` | string
`variant` | string
`condition` | string
`ownedQuantity` | number
`quantity` | number
`priceEur` | number
`negotiable` | boolean
`status` | string

## Example

```typescript
import type { SaleListingResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "collectionItemId": null,
  "cardId": null,
  "name": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "variant": null,
  "condition": null,
  "ownedQuantity": null,
  "quantity": null,
  "priceEur": null,
  "negotiable": null,
  "status": null,
} satisfies SaleListingResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SaleListingResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


