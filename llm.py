import openai
import os

class LLM():
    def json_prompt(self, system_prompt, prompt):
        """Takes Prompts and returns JSON response, tries DeepSeek before OpenAI"""
         
        # Try DeepSeek First
        try:
            ds_api_key = os.getenv("DS_API_KEY")
            ds_api_url = os.getenv("DS_API_URL")
            ds_name = os.getenv("DS_NAME")
            
            if not all([ds_api_key, ds_api_url, ds_name]):
                raise ValueError("Missing DeepSeek configuration environment variables")
                
            response = openai.OpenAI(
                api_key=ds_api_key,
                base_url=ds_api_url,
            ).chat.completions.create(
                model=ds_name,
                messages=[
                    {"role": "system", "content": str(system_prompt)},
                    {"role": "user", "content": str(prompt)}
                ],
                max_tokens=4000,
                temperature=0.2,
                response_format={'type': 'json_object'}
            )
            
            # The response object contains the content in the message field
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"DeepSeek Failed: {e}")
            print("Trying OpenAI...")
            
            try:
                openai_api_key = os.getenv("OPENAI_API_KEY")
                openai_api_model = os.getenv("OPENAI_API_MODEL")
                
                if not all([openai_api_key, openai_api_model]):
                    raise ValueError("Missing OpenAI configuration environment variables")
                
                response = openai.OpenAI(
                    api_key=openai_api_key,
                ).chat.completions.create(
                    model=openai_api_model,
                    messages=[
                        {"role": "system", "content": str(system_prompt)},
                        {"role": "user", "content": str(prompt)}
                    ],
                    max_tokens=4000,
                    temperature=0.2,
                    response_format={'type': 'json_object'}
                )
                
                # Print for debugging
                print(response.choices[0].message.content)
                
                # Return the raw JSON string
                return response.choices[0].message.content
                
            except Exception as e:
                print(f"ALL LLMS FAILED: {e}")
                raise ValueError(f"All LLM providers failed: {e}")