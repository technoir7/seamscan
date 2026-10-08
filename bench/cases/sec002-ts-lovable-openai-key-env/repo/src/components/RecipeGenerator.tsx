import { useState } from "react";
import { generateRecipe } from "@/lib/openai";

export function RecipeGenerator() {
  const [input, setInput] = useState("");
  const [recipe, setRecipe] = useState("");
  const [loading, setLoading] = useState(false);

  async function onGenerate() {
    setLoading(true);
    try {
      setRecipe(await generateRecipe(input.split(",").map((s) => s.trim())));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="eggs, spinach, feta" />
      <button onClick={onGenerate} disabled={loading}>
        {loading ? "Cooking..." : "Generate recipe"}
      </button>
      <pre className="whitespace-pre-wrap">{recipe}</pre>
    </div>
  );
}
