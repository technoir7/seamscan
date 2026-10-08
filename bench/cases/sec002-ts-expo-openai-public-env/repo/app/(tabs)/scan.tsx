import { useRef, useState } from "react";
import { Button, Text, View } from "react-native";
import { CameraView } from "expo-camera";

async function describeDish(base64: string): Promise<string> {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.EXPO_PUBLIC_OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: "What dish is this? List likely ingredients." },
            { type: "image_url", image_url: { url: `data:image/jpeg;base64,${base64}` } },
          ],
        },
      ],
    }),
  });
  const json = await res.json();
  return json.choices[0].message.content;
}

export default function ScanScreen() {
  const camera = useRef<CameraView>(null);
  const [answer, setAnswer] = useState("");

  async function snap() {
    const photo = await camera.current?.takePictureAsync({ base64: true, quality: 0.5 });
    if (photo?.base64) setAnswer(await describeDish(photo.base64));
  }

  return (
    <View style={{ flex: 1 }}>
      <CameraView ref={camera} style={{ flex: 1 }} />
      <Button title="Identify dish" onPress={snap} />
      <Text>{answer}</Text>
    </View>
  );
}
