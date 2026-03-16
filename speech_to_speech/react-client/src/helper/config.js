const DemoProfiles = [
    {
        "name": "Default - get current time",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "getDateTool",
                        "description": "get information about the date and time",
                        "inputSchema": {
                            "json": "{\"type\":\"object\",\"properties\":{},\"required\":[]}"
                        }
                    }
                }
            ]
        }
    },
    {
        "name": "MCP - get location",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [
                {
                    "toolSpec": {
                        "name": "getLocationTool",
                        "description": "Search for places, addresses.",
                        "inputSchema": {
                            "json": "{\"type\": \"object\", \"properties\": {\"tool\": {\"type\": \"string\", \"description\": \"The function name to search the location service. One of: search_places\"}, \"query\": {\"type\": \"string\", \"description\": \"The search query to find relevant information\"}}, \"required\": [\"tool\",\"query\"]}"
                        }
                    }
                }
            ]
        }
    },
    {
        "name": "Strands Agents - get weather",
        "description": "Simple demo profile with basic system prompt and toolUse like getDateTime",
        "voiceId": "matthew",
        "systemPrompt": "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.",
        "toolConfig": {
            "tools": [{
                "toolSpec": {
                    "name": "externalAgent",
                    "description": "Get weather information for specific locations.",
                    "inputSchema": {
                        "json": "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\",\"description\":\"The search query to find relevant information\"}},\"required\":[\"tool\",\"query\"]}"
                    }
                }
            }
            ]
        }
    }
];

const VoicesByLanguage = {
    "English": {
        flag: "🇺🇸🇬🇧",
        voices: [
            {
                label: "Matthew",
                value: "matthew",
                accent: "US",
                gender: "Male"
            },
            {
                label: "Tiffany",
                value: "tiffany",
                accent: "US",
                gender: "Female"
            },
            {
                label: "Amy",
                value: "amy",
                accent: "GB",
                gender: "Female"
            }
        ]
    },
    "French": {
        flag: "🇫🇷",
        voices: [
            {
                label: "Ambre",
                value: "ambre",
                accent: "FR",
                gender: "Female"
            },
            {
                label: "Florian",
                value: "florian",
                accent: "FR",
                gender: "Male"
            }
        ]
    },
    "Italian": {
        flag: "🇮🇹",
        voices: [
            {
                label: "Beatrice",
                value: "beatrice",
                accent: "IT",
                gender: "Female"
            },
            {
                label: "Lorenzo",
                value: "lorenzo",
                accent: "IT",
                gender: "Male"
            }
        ]
    },
    "German": {
        flag: "🇩🇪",
        voices: [
            {
                label: "Greta",
                value: "greta",
                accent: "DE",
                gender: "Female"
            },
            {
                label: "Lennart",
                value: "lennart",
                accent: "DE",
                gender: "Male"
            }
        ]
    },
    "Spanish": {
        flag: "🇪🇸",
        voices: [
            {
                label: "Lupe",
                value: "lupe",
                accent: "ES",
                gender: "Female"
            },
            {
                label: "Carlos",
                value: "carlos",
                accent: "ES",
                gender: "Male"
            }
        ]
    }
};

// Flatten voices for backward compatibility
const Voices = Object.values(VoicesByLanguage).flatMap(lang =>
    lang.voices.map(voice => ({
        label: `${voice.label} (${voice.accent})`,
        value: voice.value,
        ...voice
    }))
);

export { DemoProfiles, Voices, VoicesByLanguage };