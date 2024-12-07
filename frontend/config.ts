export const getApiUrl = () => {
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'local';
  
  switch (environment) {
    case 'docker':
      return 'http://0.0.0.0:8000';
    case 'local':
    default:
      return 'http://127.0.0.1:8000';
  }
};
