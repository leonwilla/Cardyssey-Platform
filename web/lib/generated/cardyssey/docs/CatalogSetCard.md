
# CatalogSetCard


## Properties

Name | Type
------------ | -------------
`id` | string
`localId` | string
`name` | string
`imageBase` | string
`rarity` | string

## Example

```typescript
import type { CatalogSetCard } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "localId": null,
  "name": null,
  "imageBase": null,
  "rarity": null,
} satisfies CatalogSetCard

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CatalogSetCard
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


