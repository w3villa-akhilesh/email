/**
 * Auth HTTP Interceptor
 * Adds Bearer token to all HTTP requests to the Admin Backend
 */

import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthTokenService } from '../services/auth-token.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private authTokenService: AuthTokenService) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    // Get token from service
    const token = this.authTokenService.getToken();

    // Clone request and add Authorization header if token exists
    if (token) {
      request = request.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    } else {
      console.warn('[ADK Auth Interceptor] No token available for request:', request.url);
    }

    // Handle errors
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          console.error('[ADK Auth Interceptor] Unauthorized (401). Token may be invalid or expired.');
          // Optionally redirect to login or show error
        } else if (error.status === 403) {
          console.error('[ADK Auth Interceptor] Forbidden (403). User does not have admin access.');
        }
        return throwError(() => error);
      })
    );
  }
}

