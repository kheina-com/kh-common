from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, List, Tuple, Union


Query = None


@unique
class Order(Enum) :
	ascending: str = 'ASC'
	ascending_nulls_first: str = 'ASC NULLS FIRST'
	ascending_nulls_last: str = 'ASC NULLS LAST'
	descending: str = 'DESC'
	descending_nulls_first: str = 'DESC NULLS FIRST'
	descending_nulls_last: str = 'DESC NULLS LAST'


@unique
class JoinType(Enum) :
	inner: str = 'INNER JOIN'
	outer: str = 'FULL OUTER JOIN'
	cross: str = 'CROSS JOIN'
	left: str = 'LEFT JOIN'
	right: str = 'RIGHT JOIN'


@unique
class Operator(Enum) :
	equal: str = '{} = {}'
	not_equal: str = '{} != {}'
	greater_than: str = '{} > {}'
	greater_than_equal_to: str = '{} >= {}'
	less_than: str = '{} < {}'
	less_than_equal_to: str = '{} <= {}'
	like: str = '{} LIKE {}'
	not_like: str = '{} NOT LIKE {}'
	within: str = '{} IN {}'
	not_in: str = '{} NOT IN {}'
	is_null: str = '{} IS NULL'
	is_not_null: str = '{} IS NOT NULL'


@dataclass
class Value :
	value: Any
	function: str = None

	def __str__(self) :
		if self.function :
			return f'{self.function}(%s)'
		return '%s'

	def params(self) -> Any :
		yield self.value


@dataclass
class Field :
	table: str
	column: str
	function: str = None

	def __str__(self) :
		if self.function :
			return f'{self.function}({self.table}.{self.column})'
		return f'{self.table}.{self.column}'

	def __hash__(self) :
		return hash(str(self))


@dataclass
class Where :
	field: Union[Field, Value, Query]
	operator: Operator
	value: Union[Field, Value, Query]

	def __str__(self) :
		if self.operator in { Operator.is_null, Operator.is_not_null } :
			return self.operator.value.format(self.field)

		else :
			return self.operator.value.format(self.field, self.value)

	def params(self) -> List[Any] :
		if hasattr(self.field, 'params') :
			yield from self.field.params()

		if hasattr(self.value, 'params') and self.operator not in { Operator.is_null, Operator.is_not_null } :
			yield from self.value.params()


class Table :

	def __init__(self, string: str, alias: str = None) :
		assert string.startswith('kheina.')
		assert string.count('.') == 2
		if alias :
			self.__value__ = string + ' AS ' + alias
		
		else :
			self.__value__ = string

	def __str__(self) :
		return self.__value__

	def __hash__(self) :
		return hash(str(self))


class Join :

	def __init__(self, join_type: JoinType, table: Table) :
		assert type(join_type) == JoinType
		assert type(table) == Table

		self._join_type: JoinType = join_type
		self._table: Table = table
		self._where: List[Where] = []

	def where(self, *where: Tuple[Where]) :
		for w in where :
			assert type(w) == Where
			self._where.append(w)
		return self

	def __str__(self) :
		assert self._where
		return (
			f'{self._join_type.value} {self._table} ON ' +
			' AND '.join(list(map(str, self._where)))
		)

	def params(self) -> List[Any] :
		for where in self._where :
			yield from where.params()


class Query :

	def __init__(self, table: Table) :
		assert type(table) == Table

		self._table: str = table
		self._joins: List[Join] = []
		self._select: List[Field] = []
		self._where: List[Where] = []
		self._having: List[Where] = []
		self._group: List[Field] = []
		self._order: List[Tuple[Union[Field, Order]]] = []
		self._limit: int = None
		self._offset: int = None
		self._function: str = None


	def __build_query__(self) :
		# something needs to be selected
		assert self._select

		query = f'SELECT {",".join(list(map(str, self._select)))} FROM {self._table}'

		if self._joins :
			query += (
				' ' +
				' '.join(list(map(str, self._joins)))
			)

		if self._where :
			query += (
				' WHERE ' +
				' AND '.join(list(map(str, self._where)))
			)

		if self._group :
			query += (
				' GROUP BY ' +
				','.join(list(map(str, self._group)))
			)

		if self._having :
			query += (
				' HAVING ' +
				' AND '.join(list(map(str, self._having)))
			)

		if self._order :
			query += (
				' ORDER BY ' +
				','.join(list(map(lambda x : f'{x[0]} {x[1].value}', self._order)))
			)

		if self._limit :
			query += ' LIMIT %s'

		if self._offset :
			query += ' OFFSET %s'

		return query

	def __str__(self) :
		if self._function :
			return f'{self._function}(' + self.__build_query__() + ')'
		return '(' + self.__build_query__() + ')'

	def build(self) :
		return self.__build_query__() + ';', self.params()

	def params(self) :
		# something needs to be selected
		assert self._select

		params = []

		if self._joins :
			for join in self._joins :
				params += list(join.params())

		if self._where :
			for where in self._where :
				params += list(where.params())

		if self._having :
			for having in self._having :
				params += list(having.params())

		if self._limit :
			params.append(self._limit)

		if self._offset :
			params.append(self._offset)

		return params

	def select(self, *field: Tuple[Field]) :
		for f in field :
			assert type(f) == Field
			self._select.append(f)
		return self

	def join(self, *join: Tuple[Join]) :
		for j in join :
			assert type(j) == Join
			self._joins.append(j)
		return self

	def where(self, *where: Tuple[Where]) :
		for w in where :
			assert type(w) == Where
			self._where.append(w)
		return self

	def group(self, *field: Tuple[Field]) :
		for f in field :
			assert type(f) == Field
			self._group.append(f)
		return self

	def having(self, *having: Tuple[Where]) :
		for h in having :
			assert type(h) == Where
			self._having.append(h)
		return self

	def order(self, field: Field, order: Order) :
		assert type(field) == Field
		assert type(order) == Order
		self._order.append((field, order))
		return self

	def limit(self, records: int) :
		assert records > 0
		self._limit = records
		return self

	def offset(self, records: int) :
		assert records > 0
		self._offset = records
		return self

	def page(self, page: int) :
		assert page > 0
		assert self._limit and self._limit > 0
		self._offset = self._limit * (page - 1)
		return self

	def function(self, function: str) :
		self._function = function
		return self
