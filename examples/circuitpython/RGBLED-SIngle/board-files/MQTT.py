{
  "name": "Haptic",
  "schema": {
    "type": "object",
    "required": [
      "response",
      "values"
    ],
    "properties": {
      "values": {
        "type": "object",
        "required": [
          "sleep_steps"
        ],
        "properties": {
          "sleep_steps": {
            "type": "array",
            "items": {
              "type": "object",
              "required": [
                "typeofBuzz",
                "sleep_value"
              ],
              "properties": {
                "typeofBuzz": {
                  "enum": [
                    "long",
                    "short"
                  ],
                  "type": "string"
                },
                "sleep_value": {
                  "type": "number"
                }
              },
              "additionalProperties": false
            }
          }
        },
        "additionalProperties": false
      },
      "response": {
        "type": "string"
      }
    },
    "additionalProperties": false
  },
  "strict": true
}