import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description:
    "Gera codigo fundamentado na documentacao (RAG). Recupera trechos relevantes da base " +
    "e usa um modelo de codigo para escrever a solucao. Use quando precisar de codigo que " +
    "dependa de uma API/biblioteca cuja documentacao foi indexada no RAG.",
  args: {
    tarefa: tool.schema
      .string()
      .describe("Descricao do que gerar (ex: 'funcao GDScript que faz um CharacterBody2D pular')"),
    dominio: tool.schema
      .string()
      .optional()
      .describe("Slug do dominio no RAG (ex: docsgodotengineorg). Se omitido, escolha automatica."),
    model: tool.schema
      .string()
      .optional()
      .describe("Modelo de geracao no Ollama (padrao: qwen2.5-coder:7b)"),
    topk: tool.schema
      .number()
      .optional()
      .describe("Quantos trechos da doc recuperar (padrao: 5)"),
    contexto: tool.schema
      .string()
      .optional()
      .describe("Codigo existente do projeto para dar contexto ao gerador"),
    idioma: tool.schema
      .enum(["pt", "en"])
      .optional()
      .describe("Idioma dos comentarios do codigo (padrao: pt)"),
  },
  async execute(args, context) {
    const script = path.join(context.worktree, "programador.py")
    const cmd: string[] = ["python", script, args.tarefa]

    if (args.dominio) cmd.push("--dominio", args.dominio)
    if (args.model) cmd.push("--model", args.model)
    if (args.topk !== undefined) cmd.push("--topk", String(args.topk))
    if (args.contexto) cmd.push("--contexto", args.contexto)
    if (args.idioma) cmd.push("--idioma", args.idioma)

    const result = await Bun.$`${cmd}`.cwd(context.worktree).text()
    return result.trim()
  },
})
