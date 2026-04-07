// Supabase Edge Function: openrouter-proxy
// Proxy requests dari CLI ke OpenRouter API dengan autentikasi JWT

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const OPENROUTER_API_URL = "https://openrouter.ai/api/v1"
const OPENROUTER_API_KEY = Deno.env.get("OPENROUTER_API_KEY")!

interface ChatMessage {
  role: string
  content: string | null
  tool_calls?: any[]
}

interface ChatCompletionRequest {
  model: string
  messages: ChatMessage[]
  tools?: any[]
  tool_choice?: string
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      },
    })
  }

  try {
    // 1. Verifikasi JWT Token dari CLI
    const authHeader = req.headers.get("authorization")
    if (!authHeader?.startsWith("Bearer ")) {
      return new Response(
        JSON.stringify({ error: "Missing or invalid authorization header" }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    }

    const jwtToken = authHeader.replace("Bearer ", "")

    // Verifikasi token dengan Supabase Auth
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!
    const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY")!
    
    const supabase = createClient(supabaseUrl, supabaseAnonKey)
    const { data: { user }, error: authError } = await supabase.auth.getUser(jwtToken)

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: "Invalid or expired token" }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    }

    // 2. Parse request body
    const body: ChatCompletionRequest = await req.json()

    // 3. Check jika API key tidak diset
    if (!OPENROUTER_API_KEY) {
      return new Response(
        JSON.stringify({ 
          error: "OPENROUTER_API_KEY not configured in Edge Function secrets",
          hint: "Add OPENROUTER_API_KEY to your Edge Function secrets in Supabase Dashboard"
        }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      )
    }

    // 4. Forward request ke OpenRouter
    const openrouterResponse = await fetch(`${OPENROUTER_API_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${OPENROUTER_API_KEY}`,
        "Content-Type": "application/json",
        "HTTP-Referer": supabaseUrl, // Optional, untuk ranking di OpenRouter
        "X-Title": "Acadlabs CLI", // Optional, untuk ranking di OpenRouter
      },
      body: JSON.stringify(body),
    })

    // 5. Handle streaming response
    if (body.stream) {
      // Untuk streaming, pipe response langsung
      const reader = openrouterResponse.body?.getReader()
      const encoder = new TextEncoder()
      
      const stream = new ReadableStream({
        async start(controller) {
          if (!reader) {
            controller.close()
            return
          }
          
          try {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              controller.enqueue(value)
            }
          } catch (error) {
            controller.error(error)
          } finally {
            controller.close()
          }
        },
      })

      return new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream",
          "Access-Control-Allow-Origin": "*",
        },
      })
    }

    // 6. Handle non-streaming response
    const responseData = await openrouterResponse.json()

    if (!openrouterResponse.ok) {
      return new Response(
        JSON.stringify({ 
          error: "OpenRouter API error", 
          details: responseData 
        }),
        { 
          status: openrouterResponse.status, 
          headers: { "Content-Type": "application/json" } 
        }
      )
    }

    return new Response(JSON.stringify(responseData), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    })

  } catch (error) {
    console.error("Edge function error:", error)
    return new Response(
      JSON.stringify({ 
        error: "Internal server error", 
        message: error.message 
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    )
  }
})
