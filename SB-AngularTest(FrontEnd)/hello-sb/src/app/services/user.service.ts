import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { User } from '../user/models/user';
import { Observable, map } from 'rxjs';
//import { map } from 'rxjs/operators'

@Injectable()
export class UserService {

  constructor(private http: HttpClient) { }

  getUsers(): Observable<User[]> {
    return this.http.get<any[]>("/assets/users.json")
    .pipe(
      // Data correction for registered and balance
      map<any[], User[]>(objs => objs.map(o => <User>{
        name: o.name,
        age: o.age,
        registered: new Date(o.registered.replace(' ', '')),
        email: o.email,
        balance: Number(o.balance.replace(",", ""))
      }))
    );
  }
}
