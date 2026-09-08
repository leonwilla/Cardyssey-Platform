
# CatalogSetSummary


## Properties

Name | Type
------------ | -------------
`id` | string
`name` | string
`logo` | string
`symbol` | string
`officialCount` | number
`totalCount` | number

## Example

```typescript
import type { CatalogSetSummary } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "name": null,
  "logo": null,
  "symbol": null,
  "officialCount": null,
  "totalCount": null,
} satisfies CatalogSetSummary

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CatalogSetSummary
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


