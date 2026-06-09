import { API_BASE_URL } from "./constants";
import { errorMessages } from "./utils";

export const apiFetch = (path, options = {}) =>
  fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: options.body instanceof FormData ? options.headers : {
      ...(options.headers || {})
    }
  });

export async function parseJsonResponse(response) {
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(errorMessages(data)[0]);
    error.response = response;
    error.data = data;
    throw error;
  }
  return data;
}
