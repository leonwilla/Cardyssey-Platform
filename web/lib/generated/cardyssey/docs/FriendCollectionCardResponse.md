
# FriendCollectionCardResponse


## Properties

Name | Type
------------ | -------------
`cardId` | string
`name` | string
`setId` | string
`setName` | string
`localId` | string
`imageBase` | string
`variant` | string
`quantity` | number

## Example

```typescript
import type { FriendCollectionCardResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "cardId": null,
  "name": null,
  "setId": null,
  "setName": null,
  "localId": null,
  "imageBase": null,
  "variant": null,
  "quantity": null,
} satisfies FriendCollectionCardResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendCollectionCardResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


