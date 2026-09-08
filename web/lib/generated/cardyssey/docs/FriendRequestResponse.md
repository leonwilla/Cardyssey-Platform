
# FriendRequestResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`user` | [FriendUserResponse](FriendUserResponse.md)
`createdAt` | string

## Example

```typescript
import type { FriendRequestResponse } from 'cardyssey-contract'

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "user": null,
  "createdAt": null,
} satisfies FriendRequestResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FriendRequestResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


