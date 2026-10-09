import merge from 'lodash4/merge';
import { BrowserRouter } from 'react-router-v5';

export const mergeSettings = (a, b) => merge({}, a, b);
export { BrowserRouter };
