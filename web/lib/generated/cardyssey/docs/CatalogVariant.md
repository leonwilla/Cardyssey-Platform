
# CatalogVariant


## Properties

Name | Type
------------ | -------------
`id` | string
`type` | string
`subtype` | string
`foil` | string
`size` | string
`stamps` | Array&lt;string&gt;
`legacyVariant` | string
`tcgDexEur` | number

## Example

```typescript
import type { CatalogVariant } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "type": null,
  "subtype": null,
  "foil": null,
  "size": null,
  "stamps": null,
  "legacyVariant": null,
  "tcgDexEur": null,
} satisfies CatalogVariant

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CatalogVariant
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


