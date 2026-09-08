
# WishlistResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`cardId` | string
`languageCode` | string
`name` | string
`setId` | string
`setName` | string
`localId` | string
`imageBase` | string
`variantId` | string
`variantType` | string
`variantSubtype` | string
`foil` | string
`size` | string
`stamps` | Array&lt;string&gt;

## Example

```typescript
import type { WishlistResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "cardId": null,
  "languageCode": null,
  "name": null,
  "setId": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "variantId": null,
  "variantType": null,
  "variantSubtype": null,
  "foil": null,
  "size": null,
  "stamps": null,
} satisfies WishlistResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WishlistResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


