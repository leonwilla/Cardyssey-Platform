
# PrivacySettings


## Properties

Name | Type
------------ | -------------
`profileVisibility` | string
`showcaseVisibility` | string
`collectionVisibility` | string
`collectionValueVisibility` | string
`quantityVisibility` | string
`setsVisibility` | string
`wishlistVisibility` | string
`showcaseSize` | number

## Example

```typescript
import type { PrivacySettings } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "profileVisibility": null,
  "showcaseVisibility": null,
  "collectionVisibility": null,
  "collectionValueVisibility": null,
  "quantityVisibility": null,
  "setsVisibility": null,
  "wishlistVisibility": null,
  "showcaseSize": null,
} satisfies PrivacySettings

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PrivacySettings
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


