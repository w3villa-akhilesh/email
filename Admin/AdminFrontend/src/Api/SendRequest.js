import axios from 'axios';

const sendRequest = async ({ url, method, body, isMultipart = false, headers = {} }) => {
  try {
    const options = {
      method,
      url,
      headers,
      data: isMultipart ? body : JSON.stringify(body),
    };

    const response = await axios(options);

    if (response.status === 204) {
      return {
        success: true,
        message: "No Content"
      };
    }

    return response.data; 
  } catch (error) {
    if (error.response) {
      throw new Error(`Error: ${error.response.status} - ${error.response.data.message || error.message}`);
    } else {
      throw new Error(error.message);
    }
  }
};

export default sendRequest;