import re
import json
import requests
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _account_resource_prefix(account_id: str) -> str:
    return f"cases://account/{account_id}"


def is_authorized_case_resource(uri: str, account_id: str) -> bool:
    """Return whether a concrete MCP resource URI belongs to this account."""
    prefix = _account_resource_prefix(account_id)
    return uri == prefix or uri.startswith(f"{prefix}/")


def is_authorized_case_resource_template(uri_template: str, account_id: str) -> bool:
    """Return whether a resource template can only resolve within this account."""
    resolved_template = uri_template.replace("{account_id}", account_id)
    return is_authorized_case_resource(resolved_template, account_id)


def authorized_resource_uris(resources_available, account_id: str) -> list[str]:
    return [
        str(resource.uri)
        for resource in resources_available.resources
        if is_authorized_case_resource(str(resource.uri), account_id)
    ]


def authorized_resource_templates(templates_available, account_id: str) -> list[str]:
    return [
        str(template.uriTemplate)
        for template in templates_available.resourceTemplates
        if is_authorized_case_resource_template(str(template.uriTemplate), account_id)
    ]


async def query_cases(user_query: str, account_id: str, auth_token: str) -> str:
    async with streamablehttp_client("http://localhost:8080/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            # 1. Initialize the MCP session and discover available resources
            await session.initialize()
            resources_available = await session.list_resources()
            templates_available = await session.list_resource_templates()
            allowed_resource_uris = authorized_resource_uris(
                resources_available, account_id
            )
            allowed_resource_templates = authorized_resource_templates(
                templates_available, account_id
            )

            # 2. Ask the AI model what resources we may need
            resource_uris_requested = query_preanalysis(
                user_query,
                account_id,
                allowed_resource_uris,
                allowed_resource_templates,
                auth_token,
            )

            # 3. Request the resources from the MCP server
            mcp_context = []
            resources_used = []
            for requested_uri in resource_uris_requested:
                if not isinstance(requested_uri, str):
                    continue
                uri = requested_uri
                if not is_authorized_case_resource(uri, account_id):
                    continue
                resp = await session.read_resource(uri)
                mcp_context.append(resp.contents[0].text)
                resources_used.append(uri)

            # 4. Ask the AI model to answer the user's question with the MCP data
            response_result = generate_ai_response(
                user_query, mcp_context, account_id, auth_token
            )

            return json.dumps(
                {
                    "success": True,
                    "response": response_result,
                    "resources_used": resources_used,
                }
            )


def query_preanalysis(
    user_query,
    account_id,
    resource_uris_available,
    resource_templates_available,
    auth_token,
):
    resources_text = "\n".join(
        [f"- {uri}" for uri in resource_uris_available]
        + [f"- {template}" for template in resource_templates_available]
    )
    analysis_prompt = f"""You are an AI assistant that helps determine what case management data is needed to answer a law firm client's question.

The available MCP resources for this account are:
{resources_text or "No MCP resources are available for this account."}

Account ID: {account_id}
User Query: "{user_query}"

Based on the query and available resources, determine which MCP resource(s) should be accessed.

Respond with a JSON array of resource URIs to query, for example:
["cases://account/some-account-id/list", "cases://account/some-account-id/search/some-query"]
"""

    response_text = complete(analysis_prompt, auth_token).get("message", "")
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)

    if json_match:
        return json.loads(json_match.group())
    else:
        print("No resource array in response")
        return []


def generate_ai_response(user_query, mcp_context, account_id, auth_token):
    response_prompt = f"""You are an AI assistant answering a client's question about their legal cases. Respond in a conversational, direct tone.

Account ID: {account_id}
User Query: "{user_query}"

Case Data Retrieved from MCP Resources:
{json.dumps(mcp_context, indent=2) if mcp_context else "No case data retrieved"}

Answer the client's question based on the case data provided. Use markdown formatting for readability. Important guidelines:
- Respond directly and conversationally
- Do not include closings, signatures, or placeholders
- Start directly with the answer to their question
- Only reference the specific case data provided above
- Provide information about their cases, not legal advice
- Use markdown formatting (headers, lists, bold text, etc.) for clarity
"""
    return complete(response_prompt, auth_token).get("message", "No content")


def complete(prompt, auth_token: str):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "tokens": 1024,
    }

    response = requests.post(
        "http://app:5000/api/ai-complete",
        json=payload,
        headers={"authorization-sandbox": auth_token},
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error with AI completion: {response.json()['error']}")
