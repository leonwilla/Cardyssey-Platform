
# CardRecognitionResponse


## Properties

Name | Type
------------ | -------------
`detectedNumber` | string
`detectedQuery` | string
`candidates` | [Array&lt;CatalogCardSearchResult&gt;](CatalogCardSearchResult.md)

## Example

```typescript
import type { CardRecognitionResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "detectedNumber": null,
  "detectedQuery": null,
  "candidates": null,
} satisfies CardRecognitionResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CardRecognitionResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


