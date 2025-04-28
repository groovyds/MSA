import { NextResponse } from 'next/server';
import { OpenAI } from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();
    
    // Get the last message from the user
    const lastMessage = messages[messages.length - 1];
    
    // Generate response using OpenAI
    const completion = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: "You are a marketing strategist AI assistant. Help users analyze their presentations and provide marketing insights."
        },
        {
          role: "user",
          content: lastMessage.content
        }
      ],
    });

    // Return the response
    return NextResponse.json({
      role: "assistant",
      content: completion.choices[0].message.content,
    });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    );
  }
} 