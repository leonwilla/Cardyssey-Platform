
# ShowcaseItemResponse


## Properties

Name | Type
------------ | -------------
`collectionItemId` | string
`position` | number
`cardId` | string
`name` | string
`setName` | string
`localId` | string
`imageBase` | string
`variant` | string

## Example

```typescript
import type { ShowcaseItemResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "collectionItemId": null,
  "position": null,
  "cardId": null,
  "name": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "variant": null,
} satisfies ShowcaseItemResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ShowcaseItemResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


