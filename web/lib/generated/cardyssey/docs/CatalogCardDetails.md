
# CatalogCardDetails


## Properties

Name | Type
------------ | -------------
`id` | string
`localId` | string
`name` | string
`languageCode` | string
`imageBase` | string
`imageLanguage` | string
`setId` | string
`setName` | string
`officialCount` | number
`rarity` | string
`variants` | [Array&lt;CatalogVariant&gt;](CatalogVariant.md)

## Example

```typescript
import type { CatalogCardDetails } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "localId": null,
  "name": null,
  "languageCode": null,
  "imageBase": null,
  "imageLanguage": null,
  "setId": null,
  "setName": null,
  "officialCount": null,
  "rarity": null,
  "variants": null,
} satisfies CatalogCardDetails

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CatalogCardDetails
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


