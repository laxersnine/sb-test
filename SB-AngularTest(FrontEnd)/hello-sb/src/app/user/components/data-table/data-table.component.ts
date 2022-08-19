import { Component, OnInit, AfterViewInit, OnChanges, Input, ViewChild, SimpleChanges } from '@angular/core';
import { User } from '../../models/user';
import { MatSort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';

@Component({
  selector: 'user-data-table',
  templateUrl: './data-table.component.html',
  styleUrls: ['./data-table.component.css']
})
export class DataTableComponent implements OnInit, AfterViewInit, OnChanges {
  @Input() users: User[] = [];
  @ViewChild(MatSort) sort: MatSort | undefined;
  displayCols = ["name", "age", "registered", "email", "balance"]
  dataSource: MatTableDataSource<User>;

  constructor() { 
    this.dataSource = new MatTableDataSource(this.users);
  }

  ngOnInit(): void {
    this.dataSource.filterPredicate = (data, filter) => data.name.toLowerCase().includes(filter.toLowerCase());
  }

  ngAfterViewInit() {
    if (!!this.sort) {
      this.dataSource.sort = this.sort;
    }
  }

  onInputChange(value: string) {
    this.dataSource.filter = value;
  }

  ngOnChanges(changes: SimpleChanges) {
    if(!!changes['users'].currentValue){
      this.dataSource.data = this.users;
    }
  }

  resetBalance() {
    for(let u of this.dataSource.data)
      u.balance = 0;
  }
}
