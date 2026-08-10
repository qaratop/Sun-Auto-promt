const express = require("express");
const path = require("path");
const Anthropic = require("@anthropic-ai/sdk");

const app = express();
const port = process.env.PORT || 3000;

const anthropic = new Anthropic(); // reads ANTHROPIC_API_KEY from env

app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "public")));

app.post("/api/chat", async (req, res) => {
  const { system, messages } = req.body || {};
  if (typeof system !== "string" || !Array.isArray(messages) || !messages.length) {
    return res.status(400).json({ error: "Некорректный запрос" });
  }

  try {
    const response = await anthropic.messages.create({
      model: "claude-opus-5",
      max_tokens: 700,
      thinking: { type: "disabled" },
      system,
      messages,
    });

    const text = response.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("\n")
      .trim();

    if (!text) {
      return res.status(502).json({ error: "Пустой ответ от модели" });
    }

    res.json({ text });
  } catch (err) {
    console.error("Anthropic API error:", err.message);
    res.status(502).json({ error: "Не удалось получить ответ от модели" });
  }
});

app.listen(port, () => {
  console.log(`MoonAI Prompt Wizard listening on port ${port}`);
});
